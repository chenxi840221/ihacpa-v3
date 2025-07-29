#!/usr/bin/env python3
"""
Quick regression check for our key fixed packages
"""

import sys
import os
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vulnerability_scanner import VulnerabilityScanner

async def quick_regression_check():
    """Quick check of our key fixes"""
    scanner = VulnerabilityScanner()
    
    print("🔍 QUICK REGRESSION CHECK")
    print("=" * 50)
    print()
    
    # Test just the most critical fixes
    key_packages = [
        ('PyJWT', 'NIST'),
        ('paramiko', 'MITRE'), 
        ('tabulate', 'NIST')
    ]
    
    for package_name, scanner_type in key_packages:
        print(f"📦 Testing {package_name} ({scanner_type})")
        
        try:
            if scanner_type == 'NIST':
                result = await scanner.scan_nist_nvd(package_name)
            else:
                result = await scanner.scan_mitre_cve(package_name)
            
            count = result.get('vulnerability_count', 0)
            found = result.get('found_vulnerabilities', False)
            
            print(f"   Result: {count} vulnerabilities found")
            
            # Check expectations
            if package_name == 'PyJWT' and count >= 3:
                print("   ✅ PyJWT: PASS - Still finding CVEs (3+ expected)")
            elif package_name == 'paramiko' and count >= 1:
                print("   ✅ Paramiko: PASS - Still finding CVEs (1+ expected)")
            elif package_name == 'tabulate' and count == 0:
                print("   ✅ Tabulate: PASS - Correctly finding 0 CVEs")
            else:
                print(f"   ⚠️  {package_name}: Check needed - found {count} CVEs")
        
        except Exception as e:
            print(f"   💥 ERROR: {e}")
        
        print()
        # Longer delay to avoid rate limits
        await asyncio.sleep(10)
    
    await scanner.close()

if __name__ == "__main__":
    asyncio.run(quick_regression_check())