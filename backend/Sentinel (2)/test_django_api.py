#!/usr/bin/env python
"""
Django API Testing - No external dependencies needed
"""
import os
import sys
import json

# Setup Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def test_user_registration():
    """Test user registration using Django test client"""
    
    print("🔍 Testing User Registration...")
    print("-" * 50)
    
    # Create test client
    client = Client()
    
    # Test user data
    user_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "contact_no": "9876543210"
    }
    
    try:
        # Make POST request
        response = client.post(
            '/api/auth/register/',
            data=json.dumps(user_data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ User registration successful!")
            
            # Check if user was created in database
            user = User.objects.filter(email='test@example.com').first()
            if user:
                print(f"📁 User found in database: {user.email}")
                print(f"🆔 User ID: {user.id}")
                return True
            else:
                print("❌ User not found in database")
                return False
        else:
            print("❌ Registration failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_user_login():
    """Test user login using Django test client"""
    
    print("\n🔍 Testing User Login...")
    print("-" * 50)
    
    client = Client()
    
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    try:
        response = client.post(
            '/api/auth/login/',
            data=json.dumps(login_data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            token = response.json().get('access')
            print(f"🔑 JWT Token: {token[:50]}...")
            return token
        else:
            print("❌ Login failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_media_upload(token):
    """Test media upload using Django test client"""
    
    print("\n🔍 Testing Media Upload...")
    print("-" * 50)
    
    client = Client()
    
    # Create test file data (small PNG)
    test_image_content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8'
        b'\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    # Prepare headers with JWT token
    headers = {
        'HTTP_AUTHORIZATION': f'Bearer {token}'
    }
    
    try:
        response = client.post(
            '/api/assets/upload/',
            data={'file': test_image_content},
            **headers
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ Media upload successful!")
            asset_id = response.json().get('asset_id')
            file_hash = response.json().get('file_hash')
            print(f"📁 Asset ID: {asset_id}")
            print(f"🔒 File Hash: {file_hash}")
            return True
        else:
            print("❌ Upload failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_mongodb_data():
    """Check data in MongoDB"""
    
    print("\n📊 Checking MongoDB Atlas Data...")
    print("-" * 50)
    
    try:
        # Check users
        users = User.objects.all()
        print(f"👥 Total Users: {users.count()}")
        for user in users:
            print(f"   - {user.email} (ID: {user.id})")
        
        # Check assets via MongoDB connection
        from core.mongodb import asset_manager
        assets = asset_manager.get_assets()
        print(f"📁 Total Assets: {len(assets)}")
        for asset in assets:
            print(f"   - {asset['file_name']} (Hash: {asset['file_hash'][:20]}...)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Testing SENTINEL API with Django Test Client")
    print("=" * 60)
    
    # Test registration
    reg_success = test_user_registration()
    
    if reg_success:
        # Test login
        token = test_user_login()
        
        if token:
            # Test media upload
            upload_success = test_media_upload(token)
            
            # Check all data
            check_mongodb_data()
            
            if upload_success:
                print("\n🎉 All tests successful!")
                print("💡 Check your MongoDB Atlas dashboard to see the data")
            else:
                print("\n⚠️ Some tests failed")
        else:
            print("\n⚠️ Login failed")
    else:
        print("\n⚠️ Registration failed")
    
    print("\n📝 Summary:")
    print("   - User data saved in MongoDB Atlas 'users' collection")
    print("   - Asset metadata saved in MongoDB Atlas 'assets' collection")
    print("   - Files saved locally in /media/videos/")
