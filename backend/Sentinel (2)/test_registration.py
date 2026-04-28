#!/usr/bin/env python
"""
Test User Registration - Save to MongoDB Atlas
"""
import requests
import json

def test_user_registration():
    """Test user registration endpoint"""
    
    # API endpoint
    url = "http://localhost:8000/api/auth/register/"
    
    # Test user data
    user_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "contact_no": "9876543210"
    }
    
    print("🔍 Testing User Registration...")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(user_data, indent=2)}")
    print("-" * 50)
    
    try:
        # Make POST request
        response = requests.post(url, json=user_data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ User registration successful!")
            print("📁 Check your MongoDB Atlas 'users' collection")
            return True
        else:
            print("❌ Registration failed")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure Django server is running:")
        print("   python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_user_login():
    """Test user login endpoint"""
    
    url = "http://localhost:8000/api/auth/login/"
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    print("\n🔍 Testing User Login...")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(login_data, indent=2)}")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=login_data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            return response.json().get('access')
        else:
            print("❌ Login failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == '__main__':
    print("🚀 Testing SENTINEL User Registration & Login")
    print("=" * 60)
    
    # Test registration
    reg_success = test_user_registration()
    
    if reg_success:
        # Test login
        token = test_user_login()
        
        if token:
            print(f"\n🎉 JWT Token: {token[:50]}...")
            print("📝 Use this token for media upload testing")
    
    print("\n💡 After running this, check your MongoDB Atlas:")
    print("   1. Go to your Atlas cluster")
    print("   2. Browse Collections → users")
    print("   3. You should see the new user data")
