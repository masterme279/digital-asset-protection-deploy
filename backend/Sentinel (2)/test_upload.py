#!/usr/bin/env python
"""
Test Media Upload - Save to MongoDB Atlas
"""
import requests
import json
import os

def get_jwt_token():
    """Get JWT token by logging in"""
    
    # First, login to get token
    login_url = "http://localhost:8000/api/auth/login/"
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            return response.json().get('access')
        else:
            print("❌ Login failed. Run test_registration.py first")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def create_test_file():
    """Return path to test image file"""
    # Option 1: Use auto-generated test image
    # test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    # test_file_path = "test_image.png"
    # with open(test_file_path, "wb") as f:
    #     f.write(test_image_data)

    # Option 2: Use your actual image file (RECOMMENDED)
    test_file_path = r"C:\Users\Dell\OneDrive\Pictures\133879901885586801.jpg"
    
    return test_file_path

def test_media_upload(token):
    """Test media upload endpoint"""
    
    # Create test file
    test_file = create_test_file()
    
    # API endpoint
    url = "http://localhost:8000/api/assets/upload/"
    
    # Prepare headers with JWT token
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    print("🔍 Testing Media Upload...")
    print(f"URL: {url}")
    print(f"Token: {token[:50]}...")
    print("-" * 50)
    
    try:
        # Prepare file for upload
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'image/png')}
            
            # Make POST request with file
            response = requests.post(url, files=files, headers=headers)
            
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
        print(f"❌ Upload error: {e}")
        return False
    finally:
        # Clean up ONLY the auto-generated test file (NOT your real files!)
        if os.path.exists(test_file) and test_file == "test_image.png":
            os.remove(test_file)

def test_asset_list(token):
    """Test listing user's assets"""
    
    url = "http://localhost:8000/api/assets/"
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    print("\n🔍 Testing Asset List...")
    print(f"URL: {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Asset list retrieved!")
            return True
        else:
            print("❌ Failed to get assets")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Testing SENTINEL Media Upload to MongoDB Atlas")
    print("=" * 60)
    
    # Get JWT token (auto-login)
    token = get_jwt_token()
    
    if token:
        # Test media upload
        upload_success = test_media_upload(token)
        
        if upload_success:
            # Test asset list
            test_asset_list(token)
        
        print(f"\n💡 Check your MongoDB Atlas:")
        print("   1. Go to your Atlas cluster")
        print("   2. Browse Collections → assets")
        print("   3. You should see the new asset metadata")
        print("   4. Check file_path, file_hash, and user_id fields")
    else:
        print("\n❌ Cannot proceed without JWT token")
        print("   Run test_registration.py first to create user")
