#!/usr/bin/env python3
"""
Comprehensive debugging for tabulate package issue
Test different search strategies to find the expected 7 CVEs
"""

import sys
import os
import asyncio
import json
from urllib.parse import quote

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vulnerability_scanner import VulnerabilityScanner

async def debug_tabulate_comprehensive():
    """Comprehensive tabulate debugging"""
    scanner = VulnerabilityScanner()
    
    print("🔍 COMPREHENSIVE TABULATE INVESTIGATION")
    print("Expected: 7 CVEs, Currently getting: 0 CVEs")
    print("=" * 70)
    print()
    
    # Test different search strategies
    search_terms = [
        'tabulate',
        'python tabulate',
        'tabulate python',
        'tabulate library',
        'tabulate package'
    ]
    
    for term in search_terms:
        print(f"🔎 Testing search term: '{term}'")
        base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        search_url = f"{base_url}?keywordSearch={quote(term)}"
        
        try:
            data = await scanner._rate_limited_request('nist_nvd', search_url)
            
            if data and data.get('vulnerabilities'):
                print(f"   ✅ Found {len(data['vulnerabilities'])} vulnerabilities")
                print(f"   📊 Total results: {data.get('totalResults', 'Unknown')}")
                
                relevant_count = 0
                for vuln in data['vulnerabilities']:
                    cve_data = vuln.get('cve', {})
                    cve_id = cve_data.get('id', 'Unknown')
                    
                    descriptions = cve_data.get('descriptions', [])
                    description = descriptions[0].get('value', '') if descriptions else ''
                    
                    # Check if this is actually about Python tabulate
                    desc_lower = description.lower()
                    
                    # Check for Python context
                    python_indicators = [
                        'python', 'pypi', 'pip install', 'import tabulate',
                        'python package', 'python library', 'python module'
                    ]
                    
                    # Check for WordPress/CMS exclusions
                    cms_indicators = [
                        'wordpress plugin', 'wordpress theme', 'wp plugin', 'wp theme',
                        'drupal module', 'joomla extension', 'php plugin'
                    ]
                    
                    has_python_context = any(indicator in desc_lower for indicator in python_indicators)
                    has_cms_context = any(indicator in desc_lower for indicator in cms_indicators)
                    
                    if has_python_context and not has_cms_context:
                        relevant_count += 1
                        print(f"   🐍 Potentially relevant CVE: {cve_id}")
                        print(f"      📝 {description[:200]}...")
                    elif has_cms_context:
                        print(f"   🚫 WordPress/CMS CVE: {cve_id}")
                    else:
                        print(f"   ❓ Ambiguous CVE: {cve_id}")
                        print(f"      📝 {description[:200]}...")
                
                print(f"   🎯 Potentially relevant CVEs: {relevant_count}")
                print()
            else:
                print(f"   ❌ No vulnerabilities found")
                print()
        
        except Exception as e:
            print(f"   💥 Error: {e}")
            print()
        
        # Add delay between requests
        await asyncio.sleep(2)
    
    # Test CPE-based search (Common Platform Enumeration)
    print("🔍 Testing CPE-based search...")
    cpe_search_url = f"{base_url}?cpeName=cpe:2.3:a:*:tabulate:*:*:*:*:*:*:*:*"
    
    try:
        data = await scanner._rate_limited_request('nist_nvd', cpe_search_url)
        if data and data.get('vulnerabilities'):
            print(f"   ✅ CPE search found {len(data['vulnerabilities'])} vulnerabilities")
            for vuln in data['vulnerabilities']:
                cve_id = vuln.get('cve', {}).get('id', 'Unknown')
                print(f"   📍 CPE CVE: {cve_id}")
        else:
            print("   ❌ No CPE matches found")
    except Exception as e:
        print(f"   💥 CPE search error: {e}")
    print()
    
    # Test with vendor/product specific search
    print("🔍 Testing vendor/product search...")
    vendor_search_url = f"{base_url}?keywordSearch={quote('python tabulate library')}"
    
    try:
        data = await scanner._rate_limited_request('nist_nvd', vendor_search_url)
        if data and data.get('vulnerabilities'):
            print(f"   ✅ Vendor search found {len(data['vulnerabilities'])} vulnerabilities")
        else:
            print("   ❌ No vendor matches found")
    except Exception as e:
        print(f"   💥 Vendor search error: {e}")
    
    await scanner.close()

if __name__ == "__main__":
    asyncio.run(debug_tabulate_comprehensive())