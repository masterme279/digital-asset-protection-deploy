#!/usr/bin/env python
"""
Test user creation directly
"""
import os
import sys

# Setup Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from accounts.models import User

if __name__ == '__main__':
    try:
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User',
            contact_no='9876543210'
        )
        print("User created:", user.email)
        print("User ID:", user.id)
    except Exception as e:
        print("Error:", e)
        print("Error type:", type(e).__name__)
