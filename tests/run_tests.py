#!/usr/bin/env python3
"""Run all tests."""
import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run tests using pytest."""
    try:
        # Run pytest on the tests directory
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(Path(__file__).parent),
            "-v"
        ], cwd=Path(__file__).parent.parent, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("pytest not found. Installing test dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest"], check=True)
        return run_tests()

if __name__ == "__main__":
    sys.exit(run_tests())