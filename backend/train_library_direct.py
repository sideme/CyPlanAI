#!/usr/bin/env python3
"""
Directly train documents from library folder (faster, no API needed)
"""
import os
import sys
from pathlib import Path

# Add project path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from services.document_loader import DocumentLoader

# Configuration
LIBRARY_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "library")
LIBRARY_NAME = "cybersecurity_frameworks"

def train_documents():
    """Train documents directly"""
    print("=" * 60)
    print("CyPlanAI Document Training System")
    print("=" * 60)
    print()
    
    # Check library folder
    if not os.path.isdir(LIBRARY_FOLDER):
        print(f"✗ Error: Library folder not found")
        print(f"  Expected path: {LIBRARY_FOLDER}")
        print(f"  Current working directory: {os.getcwd()}")
        sys.exit(1)
    
    # List all supported files
    supported_extensions = {'.pdf', '.txt', '.md', '.markdown', '.docx'}
    all_files = []
    for ext in supported_extensions:
        all_files.extend(Path(LIBRARY_FOLDER).glob(f"*{ext}"))
        all_files.extend(Path(LIBRARY_FOLDER).glob(f"*{ext.upper()}"))
    
    # Filter out system files
    all_files = [f for f in all_files if not f.name.startswith('.') and f.name != '.DS_Store']
    
    if not all_files:
        print(f"✗ Error: No supported document files found in library folder")
        print(f"  Supported formats: PDF, TXT, MD, DOCX")
        print(f"  Folder path: {LIBRARY_FOLDER}")
        sys.exit(1)
    
    print(f"✓ Found {len(all_files)} document files")
    print("\nFile list:")
    for i, file_path in enumerate(all_files, 1):
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"  {i}. {file_path.name} ({size_mb:.2f} MB)")
    print()
    
    # Confirm
    print(f"Knowledge base name: {LIBRARY_NAME}")
    confirm = input("\nStart training? (y/n, default y): ").strip().lower()
    if confirm == 'n':
        print("Cancelled")
        sys.exit(0)
    
    # Initialize Flask app context (for database access)
    app = create_app()
    
    with app.app_context():
        try:
            # Initialize document loader
            print("\nInitializing document loader...")
            doc_loader = DocumentLoader()
            print("✓ Document loader initialized successfully")
            print()
            
            # Process each file
            print("=" * 60)
            print("Starting document processing...")
            print("=" * 60)
            print()
            
            successful = 0
            failed = 0
            total_chunks = 0
            
            for i, file_path in enumerate(all_files, 1):
                print(f"[{i}/{len(all_files)}] Processing: {file_path.name}")
                try:
                    result = doc_loader.process_and_store(
                        str(file_path),
                        library_name=LIBRARY_NAME
                    )
                    chunks = result.get('chunks', 0)
                    total_chunks += chunks
                    successful += 1
                    print(f"  ✓ Success: {chunks} chunks, {result.get('total_chars', 0)} characters")
                except Exception as e:
                    failed += 1
                    print(f"  ✗ Failed: {str(e)}")
                print()
            
            # Summary
            print("=" * 60)
            print("Training completed!")
            print("=" * 60)
            print(f"Successful: {successful} files")
            print(f"Failed: {failed} files")
            print(f"Total: {total_chunks} document chunks")
            print()
            
            # List all libraries
            libraries = doc_loader.get_all_libraries()
            print(f"Current knowledge bases: {', '.join(libraries) if libraries else 'None'}")
            print()
            
            # Test search
            print("=" * 60)
            print("Testing search functionality...")
            print("=" * 60)
            test_queries = [
                "NIST Cybersecurity Framework",
                "ISO 27001",
                "adversarial machine learning"
            ]
            
            for query in test_queries:
                try:
                    results = doc_loader.search(query=query, n_results=2, library_filter=LIBRARY_NAME)
                    print(f"\nQuery: '{query}'")
                    print(f"Found {len(results)} results")
                    if results:
                        for j, result in enumerate(results[:2], 1):
                            source = result.get('metadata', {}).get('source', 'Unknown')
                            content_preview = result.get('content', '')[:100]
                            print(f"  {j}. [{source}] {content_preview}...")
                except Exception as e:
                    print(f"Query '{query}' failed: {str(e)}")
            
            print()
            print("=" * 60)
            print("✓ Training completed! You can now use these documents in the AI agent")
            print("=" * 60)
            print()
            print("Example questions:")
            print("  - 'What is NIST Cybersecurity Framework?'")
            print("  - 'What are the main controls in ISO 27001?'")
            print("  - 'What types of adversarial machine learning threats exist?'")
            print("  - 'What is the main content of NIST AI RMF framework?'")
            print()
            
        except Exception as e:
            print(f"\n✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    train_documents()

