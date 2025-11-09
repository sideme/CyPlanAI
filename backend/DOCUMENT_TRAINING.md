# Document Training Guide

## Overview

This system can vectorize the documents in your `library` directory and load them into the AI agent knowledge base so that conversations can ground their answers in those sources.

## Capabilities

- Supports PDF, Markdown, TXT, and DOCX files
- Automatically splits documents into chunks and generates embeddings
- Performs semantic search based on vector similarity
- Works with the DeepSeek API (for chat) and OpenAI embeddings
- Provides basic library management (create, delete, list, search)

## Setup Steps

### 1. Install dependencies

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Add the following to `backend/.env`:

```bash
# DeepSeek settings
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
LLM_PROVIDER=deepseek

# Vector database settings (optional overrides)
VECTOR_DB_PATH=./vector_db
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

**Note:** DeepSeek does not currently expose an embedding API. Use OpenAI embeddings instead by supplying `OPENAI_API_KEY`, or update these settings if DeepSeek adds embedding support in the future.

### 3. Start the services

```bash
# Terminal 1: Flask API
python3 app.py

# Terminal 2: LangGraph server
python3 langgraph_server.py
```

## Upload documents through the API

### Method 1: Upload a single file

```bash
curl -X POST http://localhost:8088/api/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/your/document.pdf" \
  -F "library_name=my_library"
```

### Method 2: Upload an entire directory

```bash
curl -X POST http://localhost:8088/api/documents/upload-directory \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/path/to/documents",
    "library_name": "my_library"
  }'
```

### Method 3: Use a Python script

```python
import requests

# Authenticate and obtain a JWT
login_response = requests.post(
    "http://localhost:8088/api/auth/login",
    json={"email": "your_email@example.com", "password": "your_password"},
)
token = login_response.json()["access_token"]

# Upload one document
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8088/api/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": f},
        data={"library_name": "my_library"},
    )
print(response.json())
```

## API endpoints

### Upload a document
- **POST** `/api/documents/upload`
  - Parameters: `file` (required), `library_name` (optional, defaults to `"default"`)
  - Response: processing result

### Upload a directory
- **POST** `/api/documents/upload-directory`
  - Body: `{"directory_path": "...", "library_name": "..."}`
  - Response: list of upload results

### List libraries
- **GET** `/api/documents/libraries`
  - Response: array of libraries

### Delete a library
- **DELETE** `/api/documents/libraries/<library_name>`
  - Response: deletion status

### Search documents
- **POST** `/api/documents/search`
  - Body: `{"query": "...", "n_results": 5, "library": "..."}`
  - Response: matching document chunks

## Workflow summary

1. **Prepare documents**: collect your PDFs, Markdown files, TXT files, and DOCX files in the `library` folder.
2. **Upload documents**: use any of the methods above to send them to the backend.
3. **Automatic processing**: the backend parses each file, splits it into chunks, generates embeddings, and stores them in ChromaDB.
4. **Intelligent retrieval**: when a user asks a question, the agent performs a semantic search, adds the relevant chunks to the prompt, and answers with grounded context.

## Example: Training documentation for Python libraries

```python
import os
import requests

API_URL = "http://localhost:8088"
EMAIL = "your_email@example.com"
PASSWORD = "your_password"
LIBRARY_NAME = "python_libraries"

# 1. Authenticate
login = requests.post(
    f"{API_URL}/api/auth/login",
    json={"email": EMAIL, "password": PASSWORD},
)
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Upload multiple files
documents_dir = "./python_docs"
for filename in os.listdir(documents_dir):
    if filename.endswith((".pdf", ".md", ".txt")):
        filepath = os.path.join(documents_dir, filename)
        with open(filepath, "rb") as f:
            response = requests.post(
                f"{API_URL}/api/documents/upload",
                headers=headers,
                files={"file": f},
                data={"library_name": LIBRARY_NAME},
            )
        print(f"Uploaded {filename}: {response.json()}")

# 3. Verify the upload
libraries = requests.get(
    f"{API_URL}/api/documents/libraries",
    headers=headers,
)
print(f"Libraries: {libraries.json()}")
```

## Test the search workflow

After the upload finishes, ask questions through the agent UI or the API and confirm that relevant document snippets are returned. Example prompts:

- "Where is the API reference for this library?"
- "Show me how to use feature X."
- "Provide an example for capability Y."

## Notes and recommendations

1. **Embedding provider**: when DeepSeek is selected, configure an OpenAI embedding key because DeepSeek does not provide embeddings yet.
2. **Document size**: large files are chunked automatically—each chunk is approximately 1,000 characters by default.
3. **Storage path**: embeddings are stored in `backend/vector_db` unless you override `VECTOR_DB_PATH`.
4. **Performance**: the initial run may take time depending on document size and network latency to the embedding provider.
5. **Token limits**: ensure the selected LLM has enough context window to include the retrieved chunks.

## Troubleshooting

### Upload fails
- Verify that the file type is supported.
- Check that the JWT token is valid.
- Review backend logs for stack traces.

### Search returns no results
- Confirm the documents were uploaded successfully.
- Double-check the `library_name` you supplied.
- Try broader or alternative search terms.

### Embedding errors
- Ensure the embedding API key is present and valid.
- If you rely on DeepSeek, supply `OPENAI_API_KEY` for embeddings.

## Next steps

- Tune `CHUNK_SIZE` and `CHUNK_OVERLAP` for your content.
- Add parsers for additional document formats.
- Implement document versioning if needed.
- Build a document preview experience for the UI.

