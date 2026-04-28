#!/usr/bin/env python
"""
Test MongoDB Connection for SENTINEL
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from core.mongodb import mongo_connection, asset_manager

def test_mongodb_connection():
    """Test MongoDB connection and basic operations"""
    try:
        print("Testing MongoDB connection...")
        
        # Test connection
        db = mongo_connection.db
        print(f"Connected to database: {db.name}")
        
        # Test collection access
        collection = mongo_connection.get_collection('test')
        print("Collection access successful")
        
        # Test insert operation
        test_doc = {
            'test': True,
            'message': 'MongoDB connection test',
            'timestamp': mongo_connection.db.command('serverStatus')['localTime']
        }
        
        result = collection.insert_one(test_doc)
        print(f"Test document inserted with ID: {result.inserted_id}")
        
        # Test find operation
        found_doc = collection.find_one({'_id': result.inserted_id})
        print(f"Test document retrieved: {found_doc['message']}")
        
        # Clean up
        collection.delete_one({'_id': result.inserted_id})
        print("Test document cleaned up")
        
        # Test asset manager
        print("\nTesting AssetManager...")
        
        # Create test asset
        test_asset = {
            'user_id': 'test_user_123',
            'file_name': 'test_video.mp4',
            'file_path': '/media/videos/test_video.mp4',
            'file_hash': 'test_hash_123',
            'metadata': {
                'size': 1024,
                'content_type': 'video/mp4'
            },
            'fingerprints': {
                'phash': None,
                'dhash': None,
                'video': None
            }
        }
        
        asset_id = asset_manager.insert_asset(test_asset)
        print(f"Test asset created with ID: {asset_id}")
        
        # Retrieve asset
        retrieved_asset = asset_manager.get_asset_by_id(asset_id)
        print(f"Asset retrieved: {retrieved_asset['file_name']}")
        
        # Clean up test asset
        asset_manager.delete_asset(asset_id)
        print("Test asset cleaned up")
        
        print("\nMongoDB connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"MongoDB connection test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_mongodb_connection()
    sys.exit(0 if success else 1)
