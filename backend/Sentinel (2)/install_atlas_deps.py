#!/usr/bin/env python
"""
Install MongoDB Atlas dependencies
"""
import subprocess
import sys

def install_dependencies():
    """Install required packages for MongoDB Atlas"""
    packages = [
        'pymongo[srv]==4.6.0',
        'dnspython==2.4.2'
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ {package} installed successfully")
            else:
                print(f"✗ Failed to install {package}: {result.stderr}")
        except Exception as e:
            print(f"Error installing {package}: {e}")

if __name__ == '__main__':
    install_dependencies()
