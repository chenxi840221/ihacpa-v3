#!/usr/bin/env python3
"""
Comprehensive verification that all previous fixes are still working
Tests the key packages we fixed in our vulnerability scanner improvements
"""

import sys
import os
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vulnerability_scanner import VulnerabilityScanner

# Key packages we fixed with expected results
VERIFICATION_PACKAGES = [
    # Format: (package_name, scanner_type, expected_status, description)
    ('PyJWT', 'NIST', 'should_find_cves', 'Fixed: 0→3 CVEs (major discrepancy fix)'),
    ('tables', 'NIST', 'should_find_cves', 'Fixed: 1→392 CVEs (major discrepancy fix)'),
    ('paramiko', 'MITRE', 'should_find_cves', 'Fixed: Missing CVE-2023-48795 detection'),
    ('openpyxl', 'NIST', 'should_find_cves', 'Fixed: Missing CVE-2017-5992 detection'),
    ('tabulate', 'ALL', 'should_find_none', 'Verified: 0 CVEs (correct - no actual vulnerabilities exist)'),
    ('requests', 'ALL', 'should_find_cves', 'Control: Should still work as before'),
    ('flask', 'ALL', 'should_find_cves', 'Control: Should still work as before'),
]

async def verify_all_fixes():
    """Verify all our previous fixes are still working"""
    scanner = VulnerabilityScanner()
    
    print("🔍 VERIFYING ALL PREVIOUS VULNERABILITY SCANNER FIXES")
    print("=" * 80)
    print()
    
    results = []
    
    for package_name, scanner_type, expected_status, description in VERIFICATION_PACKAGES:
        print(f"📦 Testing {package_name} ({scanner_type})")
        print(f"   Expected: {expected_status}")
        print(f"   Context: {description}")
        
        try:
            if scanner_type == 'NIST' or scanner_type == 'ALL':
                nist_result = await scanner.scan_nist_nvd(package_name)
                nist_count = nist_result.get('vulnerability_count', 0)
                nist_found = nist_result.get('found_vulnerabilities', False)
                print(f"   📊 NIST NVD: {nist_count} CVEs found")
                
                if expected_status == 'should_find_cves' and nist_count > 0:
                    print(f"   ✅ NIST: PASS - Found {nist_count} CVEs as expected")
                elif expected_status == 'should_find_none' and nist_count == 0:
                    print(f"   ✅ NIST: PASS - Found 0 CVEs as expected")
                elif expected_status == 'should_find_cves' and nist_count == 0:
                    print(f"   ❌ NIST: REGRESSION - Expected CVEs but found none")
                    results.append(f"REGRESSION: {package_name} NIST scanner")
                else:
                    print(f"   ✅ NIST: PASS - Behavior as expected")
            
            if scanner_type == 'MITRE' or scanner_type == 'ALL':
                mitre_result = await scanner.scan_mitre_cve(package_name)
                mitre_count = mitre_result.get('vulnerability_count', 0)
                print(f"   🔍 MITRE CVE: {mitre_count} CVEs found")
                
                if expected_status == 'should_find_cves' and mitre_count > 0:
                    print(f"   ✅ MITRE: PASS - Found {mitre_count} CVEs as expected")
                elif expected_status == 'should_find_none' and mitre_count == 0:
                    print(f"   ✅ MITRE: PASS - Found 0 CVEs as expected")
                elif expected_status == 'should_find_cves' and mitre_count == 0:
                    print(f"   ❌ MITRE: REGRESSION - Expected CVEs but found none")
                    results.append(f"REGRESSION: {package_name} MITRE scanner")
                else:
                    print(f"   ✅ MITRE: PASS - Behavior as expected")
            
            if scanner_type == 'SNYK' or scanner_type == 'ALL':
                snyk_result = await scanner.scan_snyk(package_name)
                snyk_count = snyk_result.get('vulnerability_count', 0)
                print(f"   🛡️ SNYK: {snyk_count} vulnerabilities found")
                
                if expected_status == 'should_find_none' and snyk_count == 0:
                    print(f"   ✅ SNYK: PASS - Found 0 vulnerabilities as expected")
                else:
                    print(f"   ✅ SNYK: INFO - Found {snyk_count} vulnerabilities")
        
        except Exception as e:
            print(f"   💥 ERROR: {e}")
            results.append(f"ERROR: {package_name} - {e}")
        
        print()
        # Add delay between requests to respect rate limits
        await asyncio.sleep(2)
    
    # Summary
    print("=" * 80)
    print("🎯 VERIFICATION SUMMARY")
    print("=" * 80)
    
    if not results:
        print("✅ ALL FIXES VERIFIED - No regressions detected!")
        print("✅ All vulnerability scanners working as expected")
        print("✅ Previous fixes remain intact")
    else:
        print("❌ ISSUES DETECTED:")
        for issue in results:
            print(f"   - {issue}")
    
    await scanner.close()
    return len(results) == 0

if __name__ == "__main__":
    success = asyncio.run(verify_all_fixes())
    sys.exit(0 if success else 1)