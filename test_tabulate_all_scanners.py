#!/usr/bin/env python3
"""
Test tabulate package across all vulnerability scanners
"""

import sys
import os
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vulnerability_scanner import VulnerabilityScanner

async def test_tabulate_all_scanners():
    scanner = VulnerabilityScanner()
    
    print('🔍 TESTING TABULATE ACROSS ALL VULNERABILITY SCANNERS')
    print('=' * 70)
    
    # Test NIST NVD
    print('📊 NIST NVD Scanner:')
    try:
        nist_result = await scanner.scan_nist_nvd('tabulate')
        print(f'   Result: {nist_result}')
    except Exception as e:
        print(f'   Error: {e}')
    print()
    
    # Test MITRE CVE
    print('🔍 MITRE CVE Scanner:')
    try:
        mitre_result = await scanner.scan_mitre_cve('tabulate')
        print(f'   Result: {mitre_result}')
    except Exception as e:
        print(f'   Error: {e}')
    print()
    
    # Test SNYK
    print('🛡️ SNYK Scanner:')
    try:
        snyk_result = await scanner.scan_snyk('tabulate')
        print(f'   Result: {snyk_result}')
    except Exception as e:
        print(f'   Error: {e}')
    print()
    
    await scanner.close()

if __name__ == "__main__":
    asyncio.run(test_tabulate_all_scanners())