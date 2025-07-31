#!/usr/bin/env python3
"""
Debug script to understand batch processing behavior
"""

import asyncio
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

from config import Config
from excel_handler import ExcelHandler
from batch_controller import BatchController, BatchConfig, ResumeOptions
from logger import ProgressLogger
from pypi_client import PyPIClient
from vulnerability_scanner import VulnerabilityScanner

async def debug_batch_processing():
    """Debug batch processing with minimal setup"""
    
    print("🔍 DEBUG: Batch Processing Test")
    print("=" * 50)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Load config
    config = Config('05-Configuration-Templates/settings-template.yaml')
    
    # Initialize components
    input_file = "2025-07-09 IHACPA Review of ALL existing PYTHON Packages - org.xlsx"
    output_file = "debug_batch_output.xlsx"
    
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    
    # Copy input to output
    import shutil
    shutil.copy2(input_file, output_file)
    print("✅ File copied")
    
    # Initialize Excel handler
    excel_handler = ExcelHandler(output_file)
    excel_handler.load_workbook()
    print("✅ Excel loaded")
    
    # Get packages
    packages = excel_handler.get_packages_to_process(package_names=['agate', 'aiobotocore'])
    print(f"✅ Found {len(packages)} packages to process")
    for pkg in packages:
        print(f"   - {pkg['package_name']} (row {pkg['row_number']})")
    
    # Initialize other components
    progress_logger = ProgressLogger(logger)
    pypi_client = PyPIClient(config.processing)
    vuln_scanner = VulnerabilityScanner(config, logger)
    
    # Initialize batch controller
    batch_controller = BatchController(config, excel_handler, logger, progress_logger)
    batch_controller.batch_config.batch_size = 2
    
    print("\n🚀 Starting batch processing...")
    print("-" * 50)
    
    # Define processor function
    async def process_package(package_data):
        """Process a single package"""
        try:
            package_name = package_data.get('package_name')
            print(f"\n📦 Processing: {package_name}")
            
            # Simulate processing
            await asyncio.sleep(0.5)  # Small delay
            
            # Create dummy updates
            updates = {
                'latest_version': '1.0.0-TEST',
                'recommendation': 'TEST UPDATE',
                'date_published': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"   ✅ Created test updates for {package_name}")
            
            return {
                'success': True,
                'package_name': package_name,
                'updates': updates
            }
            
        except Exception as e:
            print(f"   ❌ Error processing {package_name}: {e}")
            return {
                'success': False,
                'package_name': package_name,
                'error': str(e)
            }
    
    # Initialize batch processing
    await batch_controller.initialize_batch_processing(len(packages))
    
    # Process packages
    results = await batch_controller.process_packages_in_batches(packages, process_package)
    
    print("\n" + "=" * 50)
    print("📊 BATCH PROCESSING RESULTS")
    print("=" * 50)
    print(f"Total processed: {results['total_processed']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Batches completed: {results['batches_completed']}")
    
    # Check if updates were saved
    print("\n🔍 Checking if updates were saved...")
    excel_handler_check = ExcelHandler(output_file)
    excel_handler_check.load_workbook()
    
    for pkg in packages:
        row = pkg['row_number']
        package_name = pkg['package_name']
        
        # Check if test values were saved
        ws = excel_handler_check.worksheet
        latest_version = ws.cell(row=row, column=6).value  # Column F
        recommendation = ws.cell(row=row, column=23).value  # Column W
        
        if latest_version == '1.0.0-TEST' or recommendation == 'TEST UPDATE':
            print(f"✅ {package_name}: Updates were saved!")
        else:
            print(f"❌ {package_name}: Updates NOT saved")
            print(f"   - latest_version: {latest_version}")
            print(f"   - recommendation: {recommendation}")
    
    excel_handler_check.workbook.close()
    
    print("\n✅ Debug test completed")

if __name__ == "__main__":
    asyncio.run(debug_batch_processing())