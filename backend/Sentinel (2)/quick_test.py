#!/usr/bin/env python
"""
Quick MongoDB Atlas connection test
"""
import os
from pymongo import MongoClient

def test_atlas_connection():
    """Test MongoDB Atlas connection with existing credentials"""
    
    # Get connection string from environment or use placeholder
    mongo_uri = os.environ.get('MONGO_URI', 'mongodb+srv://your_username:your_password@your-cluster.mongodb.net/sentinel')
    
    print(f"Testing connection to: {mongo_uri.split('@')[1] if '@' in mongo_uri else 'Unknown'}")
    
    try:
        # Connect to Atlas
        client = MongoClient(mongo_uri)
        
        # Test connection
        client.admin.command('ping')
        print("✅ Atlas connection successful!")
        
        # Show databases
        databases = client.list_database_names()
        print(f"📁 Available databases: {databases}")
        
        # Test sentinel database
        db = client['sentinel']
        print(f"🎯 Connected to database: {db.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPlease check:")
        print("1. Your username/password are correct")
        print("2. Your IP is whitelisted in Atlas")
        print("3. Your cluster is running")
        return False

if __name__ == '__main__':
    test_atlas_connection()
