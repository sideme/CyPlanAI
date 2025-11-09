"""
Document Loader Service - Loads and processes documents for vectorization
Supports PDF, Markdown, TXT, DOCX formats
"""
import os
from typing import List, Dict, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import pypdf
import markdown
from docx import Document as DocxDocument

from config import Config


class DocumentLoader:
    """Load and process documents for vectorization"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            length_function=len,
        )
        # Use OpenAI-compatible embeddings (works with DeepSeek or OpenAI)
        # Note: DeepSeek does not provide embedding service, so we always use OpenAI embeddings
        embedding_provider = Config.LLM_PROVIDER.lower()
        if embedding_provider == 'deepseek':
            # DeepSeek does not provide embedding API, so we use OpenAI embeddings
            # This is the standard approach when using DeepSeek for chat
            if Config.OPENAI_API_KEY:
                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=Config.OPENAI_API_KEY,
                    model="text-embedding-ada-002"
                )
            else:
                raise Exception(
                    "When using DeepSeek, you must also set OPENAI_API_KEY for embeddings. "
                    "DeepSeek does not provide embedding service."
                )
        elif Config.OPENAI_API_KEY:
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=Config.OPENAI_API_KEY,
                model="text-embedding-ada-002"
            )
        else:
            raise Exception("No embedding API key available. Please set OPENAI_API_KEY.")
        
        # Initialize ChromaDB
        os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=Config.VECTOR_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="library_documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def load_pdf(self, file_path: str) -> str:
        """Load text from PDF file"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            raise Exception(f"Error loading PDF: {str(e)}")
        return text
    
    def load_markdown(self, file_path: str) -> str:
        """Load text from Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # Convert markdown to plain text (remove markdown syntax)
                html = markdown.markdown(content)
                # Simple HTML to text conversion (basic)
                import re
                text = re.sub(r'<[^>]+>', '', html)
                return text
        except Exception as e:
            raise Exception(f"Error loading Markdown: {str(e)}")
    
    def load_txt(self, file_path: str) -> str:
        """Load text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            raise Exception(f"Error loading TXT: {str(e)}")
    
    def load_docx(self, file_path: str) -> str:
        """Load text from DOCX file"""
        try:
            doc = DocxDocument(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            raise Exception(f"Error loading DOCX: {str(e)}")
    
    def load_document(self, file_path: str) -> str:
        """Load document based on file extension"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == '.pdf':
            return self.load_pdf(file_path)
        elif ext in ['.md', '.markdown']:
            return self.load_markdown(file_path)
        elif ext == '.txt':
            return self.load_txt(file_path)
        elif ext == '.docx':
            return self.load_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def process_and_store(self, file_path: str, library_name: str = "default") -> Dict[str, Any]:
        """Process document and store in vector database"""
        # Load document
        text = self.load_document(file_path)
        
        # Split into chunks
        documents = self.text_splitter.create_documents([text])
        
        # Add metadata
        file_name = Path(file_path).name
        for i, doc in enumerate(documents):
            doc.metadata = {
                "source": file_name,
                "library": library_name,
                "chunk_index": i,
                "total_chunks": len(documents)
            }
        
        # Generate embeddings and store
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        ids = [f"{library_name}_{file_name}_{i}" for i in range(len(documents))]
        
        # Get embeddings
        embeddings_list = self.embeddings.embed_documents(texts)
        
        # Store in ChromaDB
        self.collection.add(
            embeddings=embeddings_list,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "status": "success",
            "library": library_name,
            "file": file_name,
            "chunks": len(documents),
            "total_chars": len(text)
        }
    
    def search(self, query: str, n_results: int = 5, library_filter: str = None) -> List[Dict[str, Any]]:
        """Search documents using vector similarity"""
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Build where clause for filtering
        where = {}
        if library_filter:
            where["library"] = library_filter
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where if where else None
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None
                })
        
        return formatted_results
    
    def get_all_libraries(self) -> List[str]:
        """Get list of all libraries in the database"""
        results = self.collection.get()
        libraries = set()
        if results['metadatas']:
            for meta in results['metadatas']:
                if 'library' in meta:
                    libraries.add(meta['library'])
        return sorted(list(libraries))
    
    def delete_library(self, library_name: str) -> bool:
        """Delete all documents from a specific library"""
        try:
            # Get all documents from this library
            results = self.collection.get(
                where={"library": library_name}
            )
            if results['ids']:
                self.collection.delete(ids=results['ids'])
            return True
        except Exception as e:
            print(f"Error deleting library: {str(e)}")
            return False

