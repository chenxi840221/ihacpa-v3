#!/usr/bin/env python3
"""
Extract package names from existing Excel files for v2.0 testing
"""

import openpyxl
import sys
from pathlib import Path

def extract_packages_from_excel(excel_file, max_packages=10):
    """Extract package names from Excel file"""
    try:
        workbook = openpyxl.load_workbook(excel_file, read_only=True)
        sheet = workbook.active
        
        packages = []
        
        # Look for package names in first column
        for row in sheet.iter_rows(min_row=2, max_row=max_packages+10, max_col=1):
            cell = row[0]
            if cell.value and isinstance(cell.value, str):
                # Skip headers and non-package entries
                value = cell.value.strip()
                if value and not any(skip in value.lower() for skip in ['package', 'name', 'total', 'summary']):
                    packages.append(value)
                    if len(packages) >= max_packages:
                        break
        
        workbook.close()
        return packages
        
    except Exception as e:
        print(f"Error reading {excel_file}: {e}")
        return []

def main():
    # Try recent Excel files
    excel_files = [
        "2025-07-23-updated.xlsx",
        "2025-07-23.xlsx", 
        "2025-07-22.xlsx",
        "comprehensive_format_fix.xlsx",
        "output.xlsx"
    ]
    
    print("📋 Extracting Real Package Data for v2.0 Testing")
    print("=" * 55)
    
    all_packages = set()
    
    for excel_file in excel_files:
        if Path(excel_file).exists():
            print(f"\n📄 Reading {excel_file}...")
            packages = extract_packages_from_excel(excel_file, 5)
            if packages:
                print(f"   Found packages: {', '.join(packages[:5])}")
                all_packages.update(packages)
            else:
                print("   No packages found")
    
    # Convert to list and take first 10
    package_list = list(all_packages)[:10]
    
    if package_list:
        print(f"\n📦 Test Package List ({len(package_list)} packages):")
        for i, pkg in enumerate(package_list, 1):
            print(f"   {i:2d}. {pkg}")
        
        # Save for v2.0 testing
        with open("test_packages.txt", "w") as f:
            for pkg in package_list:
                f.write(f"{pkg}\n")
        
        print(f"\n✅ Saved {len(package_list)} packages to test_packages.txt")
        
        # Also return some common packages from your project if Excel reading fails
        return package_list
    else:
        # Fallback to packages mentioned in your Excel files
        fallback_packages = [
            "requests", "urllib3", "pillow", "django", "numpy",
            "paramiko", "pyjwt", "tabulate", "cffi", "sqlalchemy",
            "markdown", "fonttools", "joblib", "terminado", "pure-eval"
        ]
        
        print(f"\n📦 Using Fallback Package List ({len(fallback_packages)} packages):")
        for i, pkg in enumerate(fallback_packages, 1):
            print(f"   {i:2d}. {pkg}")
        
        with open("test_packages.txt", "w") as f:
            for pkg in fallback_packages:
                f.write(f"{pkg}\n")
        
        print(f"\n✅ Saved {len(fallback_packages)} fallback packages to test_packages.txt")
        return fallback_packages

if __name__ == "__main__":
    packages = main()