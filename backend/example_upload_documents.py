#!/usr/bin/env python3
"""
Example script: Upload documents to knowledge base for training
"""
import requests
import os
import sys
from pathlib import Path

# Configuration
API_URL = "http://localhost:8088"
EMAIL = "your_email@example.com"  # Replace with your email
PASSWORD = "your_password"  # Replace with your password
LIBRARY_NAME = "my_library"  # Library name

def login():
    """Login and get JWT token"""
    response = requests.post(f"{API_URL}/api/auth/login", json={
        "email": EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.json()}")
        sys.exit(1)

def upload_file(token, file_path, library_name):
    """Upload a single file"""
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{API_URL}/api/documents/upload",
            headers=headers,
            files={'file': f},
            data={'library_name': library_name}
        )
    return response.json()

def upload_directory(token, directory_path, library_name):
    """Upload all documents from directory in batch"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_URL}/api/documents/upload-directory",
        headers=headers,
        json={
            "directory_path": directory_path,
            "library_name": library_name
        }
    )
    return response.json()

def list_libraries(token):
    """List all libraries"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_URL}/api/documents/libraries",
        headers=headers
    )
    return response.json()

def search_documents(token, query, library_name=None):
    """Search documents"""
    headers = {"Authorization": f"Bearer {token}"}
    data = {"query": query, "n_results": 5}
    if library_name:
        data["library"] = library_name
    response = requests.post(
        f"{API_URL}/api/documents/search",
        headers=headers,
        json=data
    )
    return response.json()

if __name__ == "__main__":
    print("=== Document Training Example ===\n")
    
    # 1. Login
    print("1. Logging in...")
    token = login()
    print("✓ Login successful\n")
    
    # 2. Upload single file example
    print("2. Upload single file example:")
    file_path = input("Enter file path (or press Enter to skip): ").strip()
    if file_path and os.path.exists(file_path):
        result = upload_file(token, file_path, LIBRARY_NAME)
        print(f"Result: {result}\n")
    else:
        print("Skipped file upload\n")
    
    # 3. Batch upload directory example
    print("3. Batch upload directory example:")
    dir_path = input("Enter directory path (or press Enter to skip): ").strip()
    if dir_path and os.path.isdir(dir_path):
        result = upload_directory(token, dir_path, LIBRARY_NAME)
        print(f"Successful: {result.get('successful', 0)} files")
        print(f"Failed: {result.get('failed', 0)} files")
        if result.get('errors'):
            print(f"Errors: {result['errors']}\n")
    else:
        print("Skipped directory upload\n")
    
    # 4. List all libraries
    print("4. List all libraries:")
    libraries = list_libraries(token)
    print(f"Library list: {libraries}\n")
    
    # 5. Search example
    print("5. Search documents example:")
    query = input("Enter search query (or press Enter to skip): ").strip()
    if query:
        results = search_documents(token, query, LIBRARY_NAME)
        print(f"Found {results.get('count', 0)} results")
        for i, result in enumerate(results.get('results', []), 1):
            print(f"\nResult {i}:")
            print(f"  Source: {result.get('metadata', {}).get('source', 'Unknown')}")
            print(f"  Content: {result.get('content', '')[:200]}...")
    
    print("\n=== Completed ===")

