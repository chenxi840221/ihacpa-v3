# NVD API HTTP 429 Optimization Plan

## 🔍 Root Cause Analysis

### Current Architecture Issues

1. **Multiple Levels of Concurrency**
   - Up to 5 packages processed simultaneously (`concurrent_requests = 5`)
   - Each package makes 5 concurrent database requests via `asyncio.gather()`
   - **Result**: Up to 25 total concurrent requests, with up to 5 hitting NVD simultaneously

2. **Race Condition in Rate Limiting** (`vulnerability_scanner.py:113-118`)
   ```python
   # RACE CONDITION: Multiple tasks execute this simultaneously
   if database in self.last_request_time:
       time_since_last = (current_time - self.last_request_time[database]).total_seconds()
       if time_since_last < rate_limit:
           await asyncio.sleep(rate_limit - time_since_last)
   
   self.last_request_time[database] = current_time  # TOO LATE!
   ```

3. **Per-Instance Rate Limiting**
   - Rate limiting is per-VulnerabilityScanner instance and per-database
   - No coordination across concurrent package processing tasks
   - Each concurrent task sees the same "old" timestamp and proceeds

4. **Insufficient Rate Limiting**
   - Current: 6-second delay between sequential requests from same instance
   - Reality: Multiple concurrent requests bypass this completely
   - NVD API limit: ~50 requests per 30 seconds (1.67 requests/second)

### Observed Symptoms

From production logs:
```
HTTP 429 for https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=Automat
HTTP 429 for https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=backcall  
HTTP 429 for https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=asttokens
HTTP 429 for https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=babel
```

**Timing Analysis**: Multiple requests check rate limits within microseconds:
- Request 1: `1753250541.699693`
- Request 2: `1753250541.700031` (0.338ms later)
- Request 3: `1753250541.700046` (0.015ms later)

## 🛠️ Solution Plan

### **Option 1: Global Rate Limiter with Async Coordination (RECOMMENDED)**

#### Implementation Strategy

1. **Create Global Rate Limiter Class**
   ```python
   class GlobalRateLimiter:
       def __init__(self):
           self._locks = {}  # Per-database locks
           self._last_request_times = {}  # Global timestamps
           self._rate_limits = {
               'nist_nvd': 2.0,  # 2 seconds between requests (conservative)
               'default': 1.0
           }
   ```

2. **Thread-Safe Rate Limiting**
   ```python
   async def acquire(self, database: str) -> None:
       if database not in self._locks:
           self._locks[database] = asyncio.Lock()
       
       async with self._locks[database]:
           current_time = datetime.now()
           rate_limit = self._rate_limits.get(database, self._rate_limits['default'])
           
           if database in self._last_request_times:
               time_since_last = (current_time - self._last_request_times[database]).total_seconds()
               if time_since_last < rate_limit:
                   sleep_time = rate_limit - time_since_last
                   await asyncio.sleep(sleep_time)
           
           # Update timestamp INSIDE the lock to prevent race conditions
           self._last_request_times[database] = datetime.now()
   ```

3. **Integration Points**
   - Modify `VulnerabilityScanner.__init__()` to accept shared rate limiter
   - Update `_rate_limited_request()` to use global rate limiter
   - Initialize shared instance in `main.py`

#### Code Changes Required

**File: `src/global_rate_limiter.py` (NEW)**
```python
import asyncio
from datetime import datetime
from typing import Dict, Optional
import logging

class GlobalRateLimiter:
    """Global rate limiter that coordinates across all concurrent requests"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._last_request_times: Dict[str, datetime] = {}
        self._rate_limits = {
            'nist_nvd': 2.0,  # 2 seconds between NVD requests (conservative)
            'mitre_cve': 1.0,
            'snyk': 1.0,
            'exploit_db': 1.0,
            'github_advisory': 1.0,
            'default': 1.0
        }
        self.logger = logger or logging.getLogger(__name__)
    
    async def acquire(self, database: str) -> None:
        """Acquire rate limit permission for database request"""
        # Create database-specific lock if it doesn't exist
        if database not in self._locks:
            self._locks[database] = asyncio.Lock()
        
        # Use async lock to prevent race conditions
        async with self._locks[database]:
            current_time = datetime.now()
            rate_limit = self._rate_limits.get(database, self._rate_limits['default'])
            
            if database in self._last_request_times:
                time_since_last = (current_time - self._last_request_times[database]).total_seconds()
                if time_since_last < rate_limit:
                    sleep_time = rate_limit - time_since_last
                    self.logger.debug(f"Rate limiting {database}: sleeping {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
            
            # Update timestamp INSIDE the lock to prevent race conditions
            self._last_request_times[database] = datetime.now()
            self.logger.debug(f"Rate limit acquired for {database}")
```

**File: `src/vulnerability_scanner.py` (MODIFIED)**
```python
# Add to constructor:
def __init__(self, timeout: int = 30, max_retries: int = 3, rate_limit: float = 1.0,
             openai_api_key: Optional[str] = None, ai_enabled: bool = True,
             azure_endpoint: Optional[str] = None, azure_model: Optional[str] = None,
             global_rate_limiter: Optional[GlobalRateLimiter] = None):
    # ... existing code ...
    self.global_rate_limiter = global_rate_limiter

# Modify _rate_limited_request method:
async def _rate_limited_request(self, database: str, url: str, params: Dict = None) -> Optional[Dict]:
    """Make rate-limited request with global coordination"""
    
    # Use global rate limiter if available
    if self.global_rate_limiter:
        await self.global_rate_limiter.acquire(database)
    else:
        # Fallback to old logic (with race condition fix)
        await self._legacy_rate_limit(database)
    
    # ... rest of method unchanged ...
```

**File: `src/main.py` (MODIFIED)**
```python
# Add import:
from src.global_rate_limiter import GlobalRateLimiter

# In __init__ method:
def __init__(self):
    # ... existing code ...
    
    # Create shared global rate limiter
    self.global_rate_limiter = GlobalRateLimiter(logger=self.logger)
    
    # Pass shared rate limiter to vulnerability scanner
    self.vulnerability_scanner = VulnerabilityScanner(
        timeout=self.config.processing.request_timeout,
        max_retries=self.config.processing.retry_attempts,
        rate_limit=self.config.processing.rate_limit_delay,
        openai_api_key=openai_api_key,
        azure_endpoint=azure_endpoint,  
        azure_model=azure_model,
        global_rate_limiter=self.global_rate_limiter  # NEW
    )
```

### **Option 2: NVD-Specific Semaphore (SIMPLER)**

#### Implementation Strategy

1. **Add NVD Semaphore**
   ```python
   # In main.py
   self.nvd_semaphore = asyncio.Semaphore(1)  # Only 1 concurrent NVD request
   ```

2. **Semaphore-Protected Requests**
   ```python
   # In vulnerability_scanner.py
   async def scan_nist_nvd(self, package_name: str, current_version: str = None):
       if hasattr(self, 'nvd_semaphore'):
           async with self.nvd_semaphore:
               return await self._scan_nist_nvd_impl(package_name, current_version)
       else:
           return await self._scan_nist_nvd_impl(package_name, current_version)
   ```

#### Pros/Cons
- ✅ **Simple**: Easy to implement and understand
- ✅ **Effective**: Guarantees no concurrent NVD requests
- ❌ **Slower**: Serializes all NVD requests (may increase total time)
- ❌ **Less flexible**: Can't optimize for actual NVD rate limits

### **Option 3: Fix Current Race Condition (MINIMAL)**

#### Implementation Strategy

1. **Add Database-Specific Locks**
   ```python
   # In VulnerabilityScanner.__init__:
   self.rate_limit_locks = {}
   ```

2. **Lock-Protected Rate Limiting**
   ```python
   async def _rate_limited_request(self, database: str, url: str, params: Dict = None):
       if database not in self.rate_limit_locks:
           self.rate_limit_locks[database] = asyncio.Lock()
       
       async with self.rate_limit_locks[database]:
           # Existing rate limit logic here
           # ... but now protected by lock
   ```

#### Pros/Cons
- ✅ **Minimal change**: Small modification to existing code
- ❌ **Still per-instance**: Doesn't solve the fundamental concurrency issue
- ❌ **Partial solution**: May reduce but not eliminate HTTP 429 errors

## 📊 Implementation Recommendation

### **RECOMMENDED: Option 1 - Global Rate Limiter**

**Reasons:**
1. **Complete solution**: Addresses the root cause of concurrent requests
2. **Scalable**: Can handle any level of concurrency
3. **Configurable**: Easy to adjust rate limits per database
4. **Future-proof**: Foundation for advanced rate limiting strategies

**Expected Results:**
- ✅ Eliminate HTTP 429 errors from NVD API
- ✅ Maintain good performance with optimized rate limiting
- ✅ Provide foundation for other API rate limiting needs
- ⚠️ Slight increase in total execution time due to proper rate limiting

### **Fallback: Option 2 - NVD Semaphore**

If global rate limiter proves complex, implement the semaphore solution as a quick fix:
- Immediate elimination of HTTP 429 errors
- Simple to implement and test
- Can be upgraded to global rate limiter later

## 🧪 Testing Strategy

### **Unit Tests**
```python
# Test concurrent rate limiting
async def test_concurrent_nvd_requests():
    rate_limiter = GlobalRateLimiter()
    
    # Launch 10 concurrent requests
    tasks = [rate_limiter.acquire('nist_nvd') for _ in range(10)]
    start_time = time.time()
    await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Should take at least 18 seconds (9 intervals * 2 seconds)
    assert total_time >= 18.0
```

### **Integration Tests**
```python
# Test real NVD requests don't get HTTP 429
async def test_no_429_errors():
    scanner = VulnerabilityScanner(global_rate_limiter=GlobalRateLimiter())
    
    # Test with actual packages
    packages = ['requests', 'urllib3', 'certifi', 'charset-normalizer', 'idna']
    tasks = [scanner.scan_nist_nvd(pkg) for pkg in packages]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Should have no HTTP 429 errors
    for result in results:
        assert not (isinstance(result, Exception) and '429' in str(result))
```

### **Performance Tests**
- Measure impact on total execution time
- Compare before/after HTTP 429 error rates
- Validate rate limiting effectiveness

## 🚀 Deployment Plan

### **Phase 1: Implementation**
1. Create `global_rate_limiter.py`
2. Add comprehensive unit tests
3. Modify `vulnerability_scanner.py` to use global rate limiter
4. Update `main.py` to initialize shared rate limiter

### **Phase 2: Testing**
1. Run integration tests with real NVD API
2. Performance testing with full package scan
3. Validate elimination of HTTP 429 errors

### **Phase 3: Configuration**
1. Add rate limit configuration options
2. Document new rate limiting behavior
3. Add monitoring/logging for rate limit events

### **Phase 4: Monitoring**
1. Deploy with monitoring
2. Track HTTP 429 error elimination
3. Monitor performance impact
4. Fine-tune rate limits if needed

## 📈 Success Metrics

- **Primary**: Eliminate HTTP 429 errors from NVD API (target: 0 errors)
- **Secondary**: Maintain reasonable performance (target: <20% increase in total time)
- **Tertiary**: Improve reliability and reduce failed scans

## 🔧 Configuration Options

```yaml
# Add to config files
rate_limiting:
  nist_nvd_delay: 2.0      # Seconds between NVD requests
  enable_global_limiter: true
  max_concurrent_nvd: 1     # Fallback semaphore option
  
monitoring:
  log_rate_limit_events: true
  track_request_timing: false
```

This plan provides a comprehensive solution to eliminate HTTP 429 errors while maintaining good performance and setting up a foundation for future API rate limiting needs.