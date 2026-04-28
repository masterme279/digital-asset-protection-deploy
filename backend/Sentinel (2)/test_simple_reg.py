#!/usr/bin/env python
"""
Simple registration test without Django setup
"""
import requests
import json

def test_registration():
    """Test registration endpoint"""
    
    data = {
        'full_name': 'Test User',
        'email': 'test@example.com',
        'password': 'testpass123',
        'password_confirm': 'testpass123',
        'contact_no': '9876543210'
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/api/auth/register/',
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("✅ Registration successful!")
        else:
            print("❌ Registration failed")
            
    except Exception as e:
        print(f"❌ Request error: {e}")

if __name__ == '__main__':
    test_registration()
