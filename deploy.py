#!/usr/bin/env python3
"""
Deployment script for Screenshot Bookmark.
Handles installation, configuration, and startup.
"""
import os
import sys
import subprocess
import platform
from pathlib import Path


def print_banner():
    """Print deployment banner."""
    print("=" * 60)
    print("  Screenshot Bookmark - Deployment Script")
    print("=" * 60)
    print()


def check_python_version():
    """Check Python version."""
    if sys.version_info < (3, 9):
        print("[ERROR] Python 3.9 or higher is required")
        print(f"  Current version: {sys.version}")
        sys.exit(1)
    print(f"[OK] Python version: {sys.version.split()[0]}")


def check_tesseract():
    """Check if Tesseract is installed."""
    print("\nChecking Tesseract OCR...")
    tesseract_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]

    for path in tesseract_paths:
        if os.path.exists(path):
            print(f"[OK] Tesseract found: {path}")
            return path

    print("[WARNING] Tesseract not found in standard locations")
    print("  The application will use MOCK OCR for testing")
    print("  To install Tesseract:")
    if platform.system() == 'Windows':
        print("    Download from: https://github.com/UB-Mannheim/tesseract/wiki")
    elif platform.system() == 'Darwin':
        print("    brew install tesseract")
    else:
        print("    sudo apt-get install tesseract-ocr")
    return None


def install_dependencies():
    """Install Python dependencies."""
    print("\nInstalling Python dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip"
        ], check=True)

        subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", ".[web]"
        ], check=True)
        print("[OK] Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install dependencies: {e}")
        sys.exit(1)


def setup_environment():
    """Setup environment variables."""
    print("\nSetting up environment...")

    env_file = Path(".env")
    if not env_file.exists():
        print("Creating .env file from template...")
        example_file = Path(".env.example")
        if example_file.exists():
            env_file.write_text(example_file.read_text())
            print("[OK] .env file created")
            print("  Please edit .env and add your GOOGLE_API_KEY (Gemini)")
        else:
            print("[WARNING] .env.example not found")
    else:
        print("[OK] .env file already exists")


def initialize_database():
    """Initialize the database."""
    print("\nInitializing database...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "screenshot_bookmark.cli", "init"
        ], check=True, capture_output=True, text=True)
        print("[OK] Database initialized")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Database initialization failed: {e}")
        print(e.stderr)


def run_tests():
    """Run the test suite."""
    print("\nRunning tests...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "tests/", "-v"
        ], check=False)
        if result.returncode == 0:
            print("[OK] All tests passed")
        else:
            print("[WARNING] Some tests failed")
    except FileNotFoundError:
        print("[WARNING] pytest not installed, skipping tests")


def print_next_steps():
    """Print next steps."""
    print("\n" + "=" * 60)
    print("  Deployment Complete!")
    print("=" * 60)
    print()
    print("Next Steps:")
    print()
    print("1. Set your Gemini API key:")
    print("   Edit .env and set GOOGLE_API_KEY")
    print()
    print("2. Start the API server:")
    print("   python -m screenshot_bookmark.server")
    print("   (or: screenshot-bookmark-server)")
    print()
    print("3. Access the web UI:")
    print("   http://localhost:8000")
    print()
    print("4. Install the browser extension:")
    print("   - Open chrome://extensions/")
    print("   - Enable Developer mode")
    print("   - Click 'Load unpacked'")
    print("   - Select the 'extension/' folder")
    print()
    print("5. Or use the CLI:")
    print("   screenshot-bookmark --help")
    print()
    print("For Docker deployment:")
    print("   docker-compose up -d")
    print()


def main():
    """Main deployment function."""
    print_banner()
    check_python_version()
    check_tesseract()
    install_dependencies()
    setup_environment()
    initialize_database()
    run_tests()
    print_next_steps()


if __name__ == "__main__":
    main()