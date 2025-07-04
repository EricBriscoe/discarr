"""
Discarr Discord Bot - Main Entry Point
A Discord bot for monitoring Radarr and Sonarr download queues.

This is the main entry point that uses the reorganized codebase structure.
For the old implementation, see old_files_backup/
"""
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the main function from the new structure
from main import main

if __name__ == "__main__":
    exit(main())
