#!/usr/bin/env python3
"""
Demo script to show batch processing functionality
"""

import subprocess
import time
import sys
import signal
import os
from pathlib import Path

def run_batch_demo():
    """Demonstrate batch processing with interruption and resume"""
    
    print("🚀 IHACPA Batch Processing Demo")
    print("=" * 50)
    
    # Command to run batch processing
    cmd = [
        "python", "src/main.py",
        "--input", "02-Source-Data/2025-07-09 IHACPA Review of ALL existing PYTHON Packages.xlsx",
        "--output", "demo-output.xlsx", 
        "--enable-batch-processing",
        "--batch-size", "3",
        "--packages", "requests", "pandas", "numpy", "flask", "django", "scipy"
    ]
    
    print("Starting batch processing with 6 packages...")
    print("Command:", " ".join(cmd))
    print()
    
    # Start the process
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Let it run for a short time to create some checkpoints
        start_time = time.time()
        timeout = 30  # 30 seconds
        
        print("Process running... (will interrupt after 30 seconds)")
        
        while True:
            # Check if process has finished
            if process.poll() is not None:
                print("Process completed naturally")
                break
                
            # Check timeout
            if time.time() - start_time > timeout:
                print("\n⏹️  Interrupting process to demonstrate resume functionality...")
                process.terminate()
                process.wait()
                break
                
            # Read output
            try:
                output = process.stdout.readline()
                if output:
                    print(output.strip())
            except:
                pass
                
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        if process:
            process.terminate()
            process.wait()
    
    print("\n" + "=" * 50)
    print("Now let's check what checkpoints were created...")
    
    # List checkpoints
    list_cmd = [
        "python", "src/main.py",
        "--input", "02-Source-Data/2025-07-09 IHACPA Review of ALL existing PYTHON Packages.xlsx",
        "--list-checkpoints"
    ]
    
    try:
        result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
        print("Checkpoint listing output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
    except Exception as e:
        print(f"Error listing checkpoints: {e}")
    
    print("\n" + "=" * 50)
    print("To resume processing, you would run:")
    print("python src/main.py --input 'your-file.xlsx' --resume-auto")
    print("python src/main.py --input 'your-file.xlsx' --resume-from-package N")
    print("python src/main.py --input 'your-file.xlsx' --resume-from-batch N")
    
    print("\n✅ Batch processing demo completed!")
    print("\nKey features demonstrated:")
    print("- ✅ Intelligent batch processing")
    print("- ✅ Automatic checkpoint creation")
    print("- ✅ Process interruption handling")
    print("- ✅ Resume capability")

if __name__ == "__main__":
    run_batch_demo()