"""
File Hashing Module for SENTINEL
Supports chunk-based SHA256 hashing for large files
"""
import hashlib
from typing import BinaryIO


def generate_file_hash(file_obj: BinaryIO, chunk_size: int = 8192) -> str:
    """
    Generate SHA256 hash for a file using chunk-based reading
    
    Args:
        file_obj: File object (opened in binary mode)
        chunk_size: Size of each chunk to read (default: 8192 bytes)
    
    Returns:
        SHA256 hash as hexadecimal string
    
    Example:
        with open('video.mp4', 'rb') as f:
            file_hash = generate_file_hash(f)
    """
    sha256_hash = hashlib.sha256()
    
    # Remember the current position
    original_position = file_obj.tell()
    
    # Reset to beginning of file
    file_obj.seek(0)
    
    # Read file in chunks and update hash
    while chunk := file_obj.read(chunk_size):
        sha256_hash.update(chunk)
    
    # Reset file position to original
    file_obj.seek(original_position)
    
    return sha256_hash.hexdigest()


def generate_string_hash(text: str) -> str:
    """
    Generate SHA256 hash for a string
    
    Args:
        text: String to hash
    
    Returns:
        SHA256 hash as hexadecimal string
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def verify_file_integrity(file_obj: BinaryIO, expected_hash: str) -> bool:
    """
    Verify file integrity by comparing hashes
    
    Args:
        file_obj: File object (opened in binary mode)
        expected_hash: Expected SHA256 hash
    
    Returns:
        True if hashes match, False otherwise
    """
    actual_hash = generate_file_hash(file_obj)
    return actual_hash == expected_hash.lower()
