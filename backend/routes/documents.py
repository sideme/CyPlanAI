"""
Document Management Routes - Upload and manage library documents for RAG
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
from werkzeug.utils import secure_filename
from pathlib import Path
from services.document_loader import DocumentLoader

documents_bp = Blueprint('documents', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'md', 'markdown', 'docx'}

# Upload directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@documents_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_document():
    """Upload and process a document for vectorization"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        library_name = request.form.get('library_name', 'default')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        try:
            # Process and store document
            doc_loader = DocumentLoader()
            result = doc_loader.process_and_store(file_path, library_name=library_name)
            
            # Clean up uploaded file after processing
            os.remove(file_path)
            
            return jsonify({
                'message': 'Document uploaded and processed successfully',
                'data': result
            }), 200
        
        except Exception as e:
            # Clean up on error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Error processing document: {str(e)}'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@documents_bp.route('/upload-directory', methods=['POST'])
@jwt_required()
def upload_directory():
    """Upload multiple documents from a directory path"""
    try:
        data = request.get_json()
        directory_path = data.get('directory_path')
        library_name = data.get('library_name', 'default')
        
        if not directory_path:
            return jsonify({'error': 'directory_path is required'}), 400
        
        if not os.path.isdir(directory_path):
            return jsonify({'error': 'Invalid directory path'}), 400
        
        # Process all supported files in directory
        doc_loader = DocumentLoader()
        results = []
        errors = []
        
        for ext in ALLOWED_EXTENSIONS:
            pattern = f"**/*.{ext}"
            for file_path in Path(directory_path).glob(pattern):
                try:
                    result = doc_loader.process_and_store(str(file_path), library_name=library_name)
                    results.append(result)
                except Exception as e:
                    errors.append({
                        'file': str(file_path),
                        'error': str(e)
                    })
        
        return jsonify({
            'message': f'Processed {len(results)} documents',
            'successful': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Directory upload failed: {str(e)}'}), 500


@documents_bp.route('/libraries', methods=['GET'])
@jwt_required()
def list_libraries():
    """List all libraries in the vector database"""
    try:
        doc_loader = DocumentLoader()
        libraries = doc_loader.get_all_libraries()
        return jsonify({
            'libraries': libraries,
            'count': len(libraries)
        }), 200
    except Exception as e:
        return jsonify({'error': f'Error listing libraries: {str(e)}'}), 500


@documents_bp.route('/libraries/<library_name>', methods=['DELETE'])
@jwt_required()
def delete_library(library_name):
    """Delete all documents from a library"""
    try:
        doc_loader = DocumentLoader()
        success = doc_loader.delete_library(library_name)
        if success:
            return jsonify({
                'message': f'Library "{library_name}" deleted successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to delete library'}), 500
    except Exception as e:
        return jsonify({'error': f'Error deleting library: {str(e)}'}), 500


@documents_bp.route('/search', methods=['POST'])
@jwt_required()
def search_documents():
    """Search documents using vector similarity"""
    try:
        data = request.get_json()
        query = data.get('query')
        n_results = data.get('n_results', 5)
        library_filter = data.get('library')
        
        if not query:
            return jsonify({'error': 'query is required'}), 400
        
        doc_loader = DocumentLoader()
        results = doc_loader.search(query=query, n_results=n_results, library_filter=library_filter)
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

