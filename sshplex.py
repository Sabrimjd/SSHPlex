#!/usr/bin/env python3
"""SSHplex - Development wrapper for easy source usage"""

import sys
from pathlib import Path

def main():
    """Wrapper that calls the package main function directly for development."""
    # Add the sshplex package to the path
    package_path = Path(__file__).parent / "sshplex"
    if package_path.exists():
        sys.path.insert(0, str(package_path.parent))
        
        # Import and call the main function from the package
        try:
            from sshplex.main import main as package_main
            return package_main()
        except ImportError as e:
            print(f"Error importing sshplex package: {e}")
            print("Please ensure the sshplex package is properly set up.")
            return 1
    else:
        print("Error: sshplex package directory not found.")
        print("Please ensure you're running from the correct directory.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
