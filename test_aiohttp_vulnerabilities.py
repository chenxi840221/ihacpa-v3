#!/usr/bin/env python3
"""
Test what vulnerabilities should be found for aiohttp
"""

import asyncio
import sys
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from vulnerability_scanner import VulnerabilityScanner
from config import Config

async def test_aiohttp_vulnerabilities():
    """Test vulnerability scanning for aiohttp"""
    
    print("🔍 Testing Vulnerability Scanning for aiohttp")
    print("=" * 70)
    
    # First, let's manually check what CVEs exist
    print("\n1️⃣ Manual Check - Known aiohttp CVEs:")
    print("-" * 50)
    
    known_cves = [
        "CVE-2024-23334 - HTTP request smuggling vulnerability",
        "CVE-2024-23829 - Path traversal vulnerability", 
        "CVE-2023-49082 - Client session data leak",
        "CVE-2023-49081 - HTTP parser vulnerability",
        "CVE-2023-47641 - Incorrect parsing of chunk extensions",
        "CVE-2023-37276 - Cookie data leak vulnerability",
        "CVE-2021-21330 - Open redirect vulnerability"
    ]
    
    print("Known aiohttp CVEs that should be found:")
    for cve in known_cves:
        print(f"  • {cve}")
    
    # Now test our scanner
    print("\n2️⃣ Testing Our Vulnerability Scanner:")
    print("-" * 50)
    
    scanner = VulnerabilityScanner(
        timeout=30,
        max_retries=3,
        rate_limit=1.0
    )
    
    # Test scanning for aiohttp
    package_name = "aiohttp"
    current_version = "3.12.13"  # Version from results.xlsx
    
    print(f"\nScanning: {package_name} version {current_version}")
    
    try:
        results = await scanner.scan_all_databases(
            package_name=package_name,
            current_version=current_version,
            github_url="https://github.com/aio-libs/aiohttp"
        )
        
        print("\n📊 Scan Results:")
        print("-" * 50)
        
        # Check each scanner's results
        scanners = {
            'nist_nvd_result': 'NIST NVD',
            'mitre_cve_result': 'MITRE CVE',
            'snyk_result': 'SNYK',
            'exploit_db_result': 'Exploit DB'
        }
        
        for key, name in scanners.items():
            result = results.get(key, 'NOT FOUND')
            print(f"\n{name}:")
            print(f"  Result: {result}")
            
            # Check if it found any CVEs
            if result and isinstance(result, str):
                if 'cve' in result.lower() or 'vulnerability' in result.lower():
                    print(f"  ✅ Found vulnerabilities")
                elif 'none found' in result.lower() or 'not listed' in result.lower():
                    print(f"  ❌ NO vulnerabilities found (THIS IS WRONG!)")
                else:
                    print(f"  ⚠️  Unclear result")
        
    except Exception as e:
        print(f"\n❌ Error during scanning: {e}")
        import traceback
        traceback.print_exc()
    
    # Test individual scanners
    print("\n3️⃣ Testing Individual Scanners:")
    print("-" * 50)
    
    # Test NIST NVD directly
    print("\nTesting NIST NVD API directly...")
    try:
        nist_url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=aiohttp"
        response = requests.get(nist_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            total_results = data.get('totalResults', 0)
            print(f"  NIST API returned {total_results} CVEs for aiohttp")
            if total_results > 0:
                print("  First few CVEs:")
                for vuln in data.get('vulnerabilities', [])[:3]:
                    cve_id = vuln.get('cve', {}).get('id', 'Unknown')
                    print(f"    - {cve_id}")
        else:
            print(f"  API returned status: {response.status_code}")
    except Exception as e:
        print(f"  Error testing NIST API: {e}")
    
    print("\n" + "=" * 70)
    print("🔍 ANALYSIS:")
    print("=" * 70)
    print("\nIf the scanner returns 'Package version not listed' or 'None found'")
    print("for aiohttp, then there's definitely a problem with the scanning logic.")
    print("\nPossible issues:")
    print("1. Version comparison logic is broken")
    print("2. API queries are not formatted correctly")
    print("3. Results parsing is incorrect")
    print("4. Rate limiting is causing silent failures")

if __name__ == "__main__":
    asyncio.run(test_aiohttp_vulnerabilities())