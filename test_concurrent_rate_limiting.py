#!/usr/bin/env python3
"""
Test to demonstrate the race condition in NVD API rate limiting.
This test simulates the concurrent HTTP 429 errors observed in production.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import aiohttp
from src.vulnerability_scanner import VulnerabilityScanner


class MockResponse:
    """Mock response that simulates HTTP 429 after too many concurrent requests"""
    def __init__(self, status_code=429):
        self.status = status_code
    
    async def json(self):
        return {"error": "Rate limited"}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestConcurrentRateLimiting:
    """Test suite to demonstrate and validate rate limiting race conditions"""
    
    def __init__(self):
        self.request_timestamps = []
        self.concurrent_requests_count = 0
        self.max_concurrent_seen = 0
    
    async def mock_http_request(self, url, params=None):
        """Mock HTTP request that tracks timing and concurrency"""
        self.concurrent_requests_count += 1
        self.max_concurrent_seen = max(self.max_concurrent_seen, self.concurrent_requests_count)
        
        # Record the timestamp when this request starts
        timestamp = time.time()
        self.request_timestamps.append(timestamp)
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        self.concurrent_requests_count -= 1
        
        # If too many requests hit at nearly the same time, return 429
        recent_requests = [ts for ts in self.request_timestamps if timestamp - ts < 1.0]
        if len(recent_requests) > 2:  # Simulate NVD rate limit: max 2 requests per second
            return MockResponse(429)
        else:
            return MockResponse(200)
    
    async def test_race_condition_demonstration(self):
        """
        Demonstrate the race condition by simulating concurrent package processing.
        This mirrors the real-world scenario where 5 packages are processed simultaneously.
        """
        print("🧪 Testing race condition in NVD API rate limiting...")
        
        # Create a vulnerability scanner instance (simulating the shared instance in main.py)
        scanner = VulnerabilityScanner(timeout=30, rate_limit=1.0)
        
        # Mock the HTTP session to use our tracking mock
        scanner.session = MagicMock()
        scanner.session.get = AsyncMock(side_effect=self.mock_http_request)
        
        # Simulate 5 concurrent packages being processed (like in production)
        package_names = ["package1", "package2", "package3", "package4", "package5"]
        
        # Reset counters
        self.request_timestamps = []
        self.concurrent_requests_count = 0
        self.max_concurrent_seen = 0
        start_time = time.time()
        
        # Launch concurrent NVD requests (simulating the asyncio.gather in scan_databases)
        tasks = []
        for package_name in package_names:
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={package_name}"
            task = scanner._rate_limited_request('nist_nvd', url)
            tasks.append(task)
        
        # Execute all requests concurrently (this is where the race condition occurs)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results
        http_429_count = sum(1 for r in results if isinstance(r, MockResponse) and r.status == 429)
        successful_count = sum(1 for r in results if isinstance(r, MockResponse) and r.status == 200)
        
        print(f"📊 Race Condition Test Results:")
        print(f"   • Total requests: {len(package_names)}")
        print(f"   • HTTP 429 errors: {http_429_count}")
        print(f"   • Successful requests: {successful_count}")
        print(f"   • Max concurrent requests seen: {self.max_concurrent_seen}")
        print(f"   • Total execution time: {total_time:.2f}s")
        print(f"   • Request timestamps: {[f'{ts:.3f}' for ts in self.request_timestamps]}")
        
        # Analyze timing between requests
        if len(self.request_timestamps) > 1:
            sorted_timestamps = sorted(self.request_timestamps)
            min_interval = min(sorted_timestamps[i+1] - sorted_timestamps[i] 
                             for i in range(len(sorted_timestamps)-1))
            print(f"   • Minimum interval between requests: {min_interval:.3f}s")
            
            # The race condition occurs when multiple requests happen within the rate limit window
            concurrent_requests = sum(1 for i, ts in enumerate(sorted_timestamps)
                                    for j, other_ts in enumerate(sorted_timestamps)
                                    if i != j and abs(ts - other_ts) < 0.1)  # Within 100ms
            print(f"   • Requests within 100ms of each other: {concurrent_requests}")
        
        return {
            'total_requests': len(package_names),
            'http_429_errors': http_429_count,
            'successful_requests': successful_count,
            'max_concurrent': self.max_concurrent_seen,
            'race_condition_detected': http_429_count > 0
        }
    
    async def test_timing_analysis(self):
        """
        Detailed timing analysis to understand the race condition timing.
        """
        print("\n🕐 Testing detailed timing analysis...")
        
        scanner = VulnerabilityScanner(timeout=30, rate_limit=1.0)
        
        # Track exact timing of rate limit checks
        original_rate_limited_request = scanner._rate_limited_request
        check_timestamps = []
        
        async def instrumented_rate_limited_request(database, url, params=None):
            check_time = time.time()
            check_timestamps.append({
                'check_time': check_time,
                'database': database,
                'url': url,
                'last_request_time': scanner.last_request_time.get(database)
            })
            return await original_rate_limited_request(database, url, params)
        
        scanner._rate_limited_request = instrumented_rate_limited_request
        scanner.session = MagicMock()
        scanner.session.get = AsyncMock(return_value=MockResponse(200))
        
        # Run 3 concurrent requests to see the timing
        tasks = []
        for i in range(3):
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=test{i}"
            tasks.append(scanner._rate_limited_request('nist_nvd', url))
        
        await asyncio.gather(*tasks)
        
        print(f"📋 Timing Analysis Results:")
        for i, check in enumerate(check_timestamps):
            print(f"   Request {i+1}:")
            print(f"     • Check time: {check['check_time']:.6f}")
            print(f"     • Last request time: {check['last_request_time']}")
            if i > 0:
                time_diff = check['check_time'] - check_timestamps[i-1]['check_time']
                print(f"     • Time since previous check: {time_diff:.6f}s")


async def main():
    """Run the race condition tests"""
    test_suite = TestConcurrentRateLimiting()
    
    print("=" * 80)
    print("🚨 RACE CONDITION TEST: NVD API Rate Limiting")
    print("=" * 80)
    print("\nThis test demonstrates why HTTP 429 errors occur with concurrent requests.")
    print("The issue: Multiple concurrent tasks check rate limits simultaneously,")
    print("all see that enough time has passed, and make requests at the same time.")
    print()
    
    # Run the race condition demonstration
    results = await test_suite.test_race_condition_demonstration()
    
    # Run detailed timing analysis
    await test_suite.test_timing_analysis()
    
    print("\n" + "=" * 80)
    print("🔍 CONCLUSION:")
    print("=" * 80)
    
    if results['race_condition_detected']:
        print("❌ RACE CONDITION CONFIRMED: Multiple HTTP 429 errors detected")
        print("   The current rate limiting has a race condition that allows")
        print("   multiple concurrent requests to bypass the rate limit check.")
        print()
        print("🛠️  SOLUTION NEEDED:")
        print("   1. Implement global rate limiting with async locks")
        print("   2. Use a semaphore to limit concurrent NVD requests to 1")
        print("   3. Queue requests instead of allowing concurrent access")
    else:
        print("✅ No race condition detected in this test run")
        print("   (Note: Race conditions are timing-dependent and may not always occur)")
    
    print("\n📈 Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())