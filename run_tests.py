#!/usr/bin/env python3
"""
Test runner script for Discarr.
Provides easy way to run tests with proper path setup.
"""
import sys
import subprocess
from pathlib import Path

def main():
    """Run tests with proper Python path setup."""
    # Add src directory to Python path
    src_path = Path(__file__).parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Parse command line arguments
    test_args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Default to running all tests if no arguments provided
    if not test_args:
        test_args = ["tests/"]
    
    # Run pytest with the arguments
    cmd = ["python", "-m", "pytest", "--cov=src", "--cov-report=html"] + test_args
    
    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
