#!/usr/bin/env python
"""
Simple test without Django setup
"""
import os
import sys

# Add project to path
sys.path.append('c:/Users/Dell/OneDrive/Desktop/SENTINEL')

# Set environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    import django
    django.setup()
    print("✅ Django setup successful!")
    
    # Test MongoDB connection
    from core.mongodb import mongo_connection
    print("✅ MongoDB connection successful!")
    
    # Test user model
    from accounts.models import User
    print("✅ User model imported successfully!")
    
    print("\n🎉 All imports working!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")
    
    # Check what's missing
    try:
        import django
        print("✅ Django available")
    except ImportError:
        print("❌ Django not installed")
        
    try:
        import pymongo
        print("✅ PyMongo available")
    except ImportError:
        print("❌ PyMongo not installed")
