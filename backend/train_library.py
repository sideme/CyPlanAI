#!/usr/bin/env python3
"""
Train documents from the library folder
"""
import os
import sys
import requests
from pathlib import Path

# Configuration
API_URL = "http://localhost:8088"
LIBRARY_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "library")
LIBRARY_NAME = "cybersecurity_frameworks"  # Knowledge base name

def get_user_credentials():
    """Get user credentials"""
    print("=== Document Training System ===\n")
    print("Please ensure:")
    print("1. Flask API server is running (python3 app.py)")
    print("2. API keys are configured (DeepSeek or OpenAI)\n")
    
    email = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()
    
    return email, password

def login(email, password):
    """Login and get JWT token"""
    print("\nLogging in...")
    try:
        response = requests.post(f"{API_URL}/api/auth/login", json={
            "email": email,
            "password": password
        }, timeout=10)
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✓ Login successful\n")
            return token
        else:
            print(f"✗ Login failed: {response.json().get('error', 'Unknown error')}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to server {API_URL}")
        print("Please ensure Flask API server is running")
        return None
    except Exception as e:
        print(f"✗ Login error: {str(e)}")
        return None

def upload_directory(token, directory_path, library_name):
    """Upload all documents from directory in batch"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Uploading directory: {directory_path}")
    print(f"Knowledge base name: {library_name}\n")
    
    try:
        response = requests.post(
            f"{API_URL}/api/documents/upload-directory",
            headers=headers,
            json={
                "directory_path": directory_path,
                "library_name": library_name
            },
            timeout=300  # 5 minute timeout, processing large files may take time
        )
        
        if response.status_code == 200:
            result = response.json()
            successful = result.get('successful', 0)
            failed = result.get('failed', 0)
            
            print(f"✓ Upload completed!")
            print(f"  Successful: {successful} files")
            print(f"  Failed: {failed} files")
            
            if result.get('errors'):
                print("\nError details:")
                for error in result['errors']:
                    print(f"  - {error.get('file')}: {error.get('error')}")
            
            if result.get('results'):
                print("\nProcessing results:")
                for res in result['results']:
                    print(f"  - {res.get('file')}: {res.get('chunks')} chunks")
            
            return True
        else:
            print(f"✗ Upload failed: {response.json().get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"✗ Upload error: {str(e)}")
        return False

def list_libraries(token):
    """List all libraries"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{API_URL}/api/documents/libraries",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('libraries', [])
        return []
    except:
        return []

def test_search(token, library_name):
    """Test search functionality"""
    headers = {"Authorization": f"Bearer {token}"}
    test_queries = [
        "NIST Cybersecurity Framework",
        "ISO 27001 controls",
        "adversarial machine learning threats"
    ]
    
    print("\n=== Testing Search Functionality ===")
    for query in test_queries:
        try:
            response = requests.post(
                f"{API_URL}/api/documents/search",
                headers=headers,
                json={
                    "query": query,
                    "n_results": 3,
                    "library": library_name
                },
                timeout=10
            )
            if response.status_code == 200:
                results = response.json()
                count = results.get('count', 0)
                print(f"Query: '{query}' -> Found {count} results")
            else:
                print(f"Query: '{query}' -> Search failed")
        except Exception as e:
            print(f"Query: '{query}' -> Error: {str(e)}")

def main():
    """Main function"""
    # Check if library folder exists
    if not os.path.isdir(LIBRARY_FOLDER):
        print(f"✗ Error: Library folder not found: {LIBRARY_FOLDER}")
        print("Please ensure library folder exists in project root directory")
        sys.exit(1)
    
    # Check if there are PDF files in the folder
    pdf_files = list(Path(LIBRARY_FOLDER).glob("*.pdf"))
    if not pdf_files:
        print(f"✗ Warning: No PDF files found in library folder")
        print(f"Folder path: {LIBRARY_FOLDER}")
        response = input("Continue? (y/n): ").strip().lower()
        if response != 'y':
            sys.exit(0)
    else:
        print(f"✓ Found {len(pdf_files)} PDF files")
        print("File list:")
        for pdf in pdf_files[:5]:  # Show only first 5
            print(f"  - {pdf.name}")
        if len(pdf_files) > 5:
            print(f"  ... {len(pdf_files) - 5} more files")
        print()
    
    # Get user credentials
    email, password = get_user_credentials()
    
    # Login
    token = login(email, password)
    if not token:
        sys.exit(1)
    
    # Show existing libraries
    existing_libraries = list_libraries(token)
    if existing_libraries:
        print(f"Existing knowledge bases: {', '.join(existing_libraries)}")
        use_existing = input(f"\nUse existing library '{LIBRARY_NAME}'? (y/n, default y): ").strip().lower()
        if use_existing == 'n':
            LIBRARY_NAME = input("Enter new library name: ").strip() or "cybersecurity_frameworks"
    print()
    
    # Upload documents
    print("=" * 50)
    print("Starting document training...")
    print("=" * 50)
    success = upload_directory(token, LIBRARY_FOLDER, LIBRARY_NAME)
    
    if success:
        print("\n" + "=" * 50)
        print("Training completed!")
        print("=" * 50)
        
        # List all libraries
        libraries = list_libraries(token)
        print(f"\nCurrent knowledge bases: {', '.join(libraries) if libraries else 'None'}")
        
        # Test search
        test_search_choice = input("\nTest search functionality? (y/n, default y): ").strip().lower()
        if test_search_choice != 'n':
            test_search(token, LIBRARY_NAME)
        
        print("\n✓ You can now ask questions in the AI agent, and the system will automatically use these documents to answer!")
        print("\nExample questions:")
        print("  - 'What is NIST Cybersecurity Framework?'")
        print("  - 'What are the main controls in ISO 27001?'")
        print("  - 'What are adversarial machine learning threats?'")
    else:
        print("\n✗ Training failed, please check error messages")
        sys.exit(1)

if __name__ == "__main__":
    main()

