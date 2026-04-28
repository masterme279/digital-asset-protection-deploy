"""
MongoDB Connection Module for SENTINEL
Singleton pattern for database connection
"""
import os
import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from datetime import datetime
from typing import Dict, List, Optional, Any
from django.conf import settings


class MongoDBConnection:
    """
    Singleton class for MongoDB connection
    """
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()

    def _connect(self):
        try:
            mongo_uri = getattr(settings, 'MONGO_URI', None) or os.environ.get('MONGO_URI')
            if not mongo_uri:
                mongo_uri = 'mongodb://localhost:27017/sentinel'

            if 'mongodb+srv://' in mongo_uri:
                # Atlas connection with additional options
                self._client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=5000,  # 5 seconds timeout
                    connectTimeoutMS=10000,          # 10 seconds timeout
                    socketTimeoutMS=10000,           # 10 seconds timeout
                    retryWrites=True,
                    w='majority'
                )
            else:
                # Local MongoDB connection
                self._client = MongoClient(mongo_uri)

            # Test connection
            self._client.admin.command('ping')

            # Get database name from URI or use default
            # Handle Atlas URIs with query parameters
            if '?' in mongo_uri:
                db_name = mongo_uri.split('/')[-1].split('?')[0]
            else:
                db_name = mongo_uri.split('/')[-1] if '/' in mongo_uri else 'sentinel'

            self._db = self._client[db_name]

            # Detect connection type
            connection_type = "MongoDB Atlas" if 'mongodb+srv://' in mongo_uri else "Local MongoDB"
            print(f"Connected to {connection_type}: {db_name}")

        except Exception as e:
            print(f"MongoDB connection error: {e}")
            print("Please check your MONGO_URI in .env file")
            raise
    
    @property
    def db(self):
        """Get database instance"""
        return self._db
    
    @property
    def client(self):
        """Get client instance"""
        return self._client
    
    def get_collection(self, name: str) -> Collection:
        """Get a collection by name"""
        return self._db[name]
    
    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()


class AssetManager:
    """
    Asset management operations for MongoDB
    """
    
    def __init__(self):
        self.mongo = MongoDBConnection()
        self.collection = self.mongo.get_collection('assets')
    
    def insert_asset(self, asset_data: Dict[str, Any]) -> str:
        """
        Insert asset metadata into MongoDB
        
        Args:
            asset_data: Dictionary containing asset metadata
        
        Returns:
            Inserted document ID as string
        """
        # Add timestamp if not present
        if 'uploaded_at' not in asset_data:
            asset_data['uploaded_at'] = datetime.utcnow()
        
        try:
            result = self.collection.insert_one(asset_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error inserting asset: {e}")
            raise
    
    def get_assets(self, user_id: Optional[str] = None, limit: int = 20, skip: int = 0) -> List[Dict]:
        """
        Get assets from MongoDB
        
        Args:
            user_id: Filter by user ID (optional)
            limit: Maximum number of documents to return
            skip: Number of documents to skip (for pagination)
        
        Returns:
            List of asset documents
        """
        try:
            query = {}
            if user_id:
                query['user_id'] = user_id
            
            # Sort by uploaded_at descending
            cursor = self.collection.find(query).sort('uploaded_at', -1).skip(skip).limit(limit)
            
            # Convert ObjectId to string and handle datetime serialization
            assets = []
            for asset in cursor:
                asset['_id'] = str(asset['_id'])
                if 'uploaded_at' in asset and isinstance(asset['uploaded_at'], datetime):
                    asset['uploaded_at'] = asset['uploaded_at'].isoformat()
                assets.append(asset)
            
            return assets
            
        except Exception as e:
            print(f"Error fetching assets: {e}")
            raise
    
    def get_asset_by_id(self, asset_id: str) -> Optional[Dict]:
        """
        Get a single asset by ID
        
        Args:
            asset_id: Asset ID (MongoDB ObjectId as string)
        
        Returns:
            Asset document or None if not found
        """
        try:
            from bson.objectid import ObjectId
            asset = self.collection.find_one({'_id': ObjectId(asset_id)})
            
            if asset:
                asset['_id'] = str(asset['_id'])
                if 'uploaded_at' in asset and isinstance(asset['uploaded_at'], datetime):
                    asset['uploaded_at'] = asset['uploaded_at'].isoformat()
            
            return asset
            
        except Exception as e:
            print(f"Error fetching asset by ID: {e}")
            return None
    
    def get_asset_by_hash(self, file_hash: str) -> Optional[Dict]:
        """
        Get asset by file hash
        
        Args:
            file_hash: SHA256 hash of the file
        
        Returns:
            Asset document or None if not found
        """
        try:
            asset = self.collection.find_one({'file_hash': file_hash})
            
            if asset:
                asset['_id'] = str(asset['_id'])
                if 'uploaded_at' in asset and isinstance(asset['uploaded_at'], datetime):
                    asset['uploaded_at'] = asset['uploaded_at'].isoformat()
            
            return asset
            
        except Exception as e:
            print(f"Error fetching asset by hash: {e}")
            return None
    
    def update_asset(self, asset_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update asset metadata
        
        Args:
            asset_id: Asset ID (MongoDB ObjectId as string)
            update_data: Dictionary of fields to update
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            from bson.objectid import ObjectId
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            result = self.collection.update_one(
                {'_id': ObjectId(asset_id)},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Error updating asset: {e}")
            return False
    
    def delete_asset(self, asset_id: str) -> bool:
        """
        Delete asset from MongoDB
        
        Args:
            asset_id: Asset ID (MongoDB ObjectId as string)
        
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            from bson.objectid import ObjectId
            
            result = self.collection.delete_one({'_id': ObjectId(asset_id)})
            return result.deleted_count > 0
            
        except Exception as e:
            print(f"Error deleting asset: {e}")
            return False


_mongo_connection = None
_asset_manager = None


def get_mongo_connection() -> MongoDBConnection:
    global _mongo_connection
    if _mongo_connection is None:
        _mongo_connection = MongoDBConnection()
    return _mongo_connection


def get_asset_manager() -> AssetManager:
    global _asset_manager
    if _asset_manager is None:
        _asset_manager = AssetManager()
    return _asset_manager


class _LazyProxy:
    """Lazy attribute proxy to avoid connecting during module import."""

    def __init__(self, getter):
        self._getter = getter

    def __getattr__(self, item):
        return getattr(self._getter(), item)


# Backward-compatible exports used by legacy scripts/tests.
mongo_connection = _LazyProxy(get_mongo_connection)
asset_manager = _LazyProxy(get_asset_manager)
