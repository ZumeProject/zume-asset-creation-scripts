#!/usr/bin/env python3
"""
Setup script for Zume PDF Book Creator
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Zume PDF Book Creator...")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        sys.exit(1)
    
    # Install Playwright browsers
    if not run_command("playwright install chromium", "Installing Playwright browser"):
        sys.exit(1)
    
    # Create output directory
    os.makedirs("output", exist_ok=True)
    print("✅ Created output directory")
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\nYou can now run the PDF generator:")
    print("python zume_pdf_generator.py --type 10 --lang am")

if __name__ == "__main__":
    main() 