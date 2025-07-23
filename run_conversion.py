#!/usr/bin/env python3
"""
Script to run the conversion with better error handling and progress tracking.
This helps avoid timeouts and provides better visibility into the process.
"""

import subprocess
import sys
from pathlib import Path

def run_conversion(input_path: str, output_dir: str):
    """Run the conversion command with proper error handling"""
    
    cmd = [
        "uv", "run", "docs2md", 
        input_path,
        "--output-dir", output_dir,
        "--summary"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 80)
    
    try:
        # Run with real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output in real-time
        for line in process.stdout:
            print(line, end='', flush=True)
        
        # Wait for completion
        return_code = process.wait()
        
        if return_code == 0:
            print("\n" + "="*80)
            print("✅ Conversion completed successfully!")
        else:
            print(f"\n❌ Conversion failed with return code: {return_code}")
            
        return return_code
        
    except KeyboardInterrupt:
        print("\n🛑 Conversion interrupted by user")
        process.terminate()
        return 1
    except Exception as e:
        print(f"\n❌ Error running conversion: {e}")
        return 1

if __name__ == "__main__":
    input_path = "/Users/z/MEGAsync/pp/it/Piloni Stefania/presentazioni"
    output_dir = "/Users/z/Downloads/stefi2"
    
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    exit_code = run_conversion(input_path, output_dir)
    sys.exit(exit_code)