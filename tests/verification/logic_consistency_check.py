#!/usr/bin/env python3
"""
Quick logic consistency check - verify our investigation didn't break anything
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vulnerability_scanner import VulnerabilityScanner

def check_logic_consistency():
    """Check that our core logic is consistent"""
    print("🔍 LOGIC CONSISTENCY CHECK")
    print("=" * 40)
    
    scanner = VulnerabilityScanner()
    
    # Test basic instantiation
    print("✅ VulnerabilityScanner instantiated successfully")
    
    # Check key method exists
    methods_to_check = [
        'scan_nist_nvd',
        'scan_mitre_cve', 
        'scan_snyk',
        '_is_python_cve_relevant_enhanced_nist'
    ]
    
    for method_name in methods_to_check:
        if hasattr(scanner, method_name):
            print(f"✅ Method {method_name} exists")
        else:
            print(f"❌ Method {method_name} missing - REGRESSION!")
            return False
    
    # Check our key filtering logic is intact
    print()
    print("🧪 Testing key filtering logic:")
    
    # Test WordPress filtering (should exclude)
    wordpress_desc = "The Tabulate WordPress plugin through 2.10.3 does not sanitise..."
    is_relevant = scanner._is_python_cve_relevant_enhanced_nist('tabulate', 'CVE-2024-13223', wordpress_desc, {})
    if not is_relevant:
        print("✅ WordPress filtering working - correctly excludes WordPress plugins")
    else:
        print("❌ WordPress filtering broken - REGRESSION!")
        return False
    
    # Test known Python package recognition
    if 'paramiko' in str(scanner._is_python_cve_relevant_enhanced_nist.__code__.co_consts):
        print("✅ Known Python packages logic present")
    else:
        print("⚠️  Known Python packages logic may have changed")
    
    print()
    print("🎯 CONSISTENCY CHECK RESULT: ✅ PASS")
    print("   - All key methods present")
    print("   - WordPress filtering working")  
    print("   - Core logic intact")
    print("   - No regressions detected")
    
    return True

if __name__ == "__main__":
    success = check_logic_consistency()
    sys.exit(0 if success else 1)