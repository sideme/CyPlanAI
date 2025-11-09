# Library Document Training Guide

## Overview

The `library` folder should contain the reference material that you want the agent to cite, for example:
- NIST Cybersecurity Framework (NIST CSF)
- ISO 27001 annexes
- NIST AI RMF
- MITRE ATLAS
- Threat libraries (adversarial machine learning, data poisoning, etc.)
- Regulatory requirements and best practices

These files are vectorized and added to the agent knowledge base so every response can reference the authoritative sources you prepared.

## Quick start (recommended)

### Method 1: Direct training (fastest)

This script processes the documents locally without going through the REST API:

```bash
cd backend
source venv/bin/activate
python3 train_library_direct.py
```

Run through these steps first:
1. Install dependencies with `pip install -r requirements.txt`.
2. Configure API keys in `.env` (DeepSeek for chat, OpenAI for embeddings).
3. Execute the script.
4. Wait for the summary output.

### Method 2: Train through the API

Use this path when you need to trigger training remotely or from another machine.

```bash
# Terminal 1: start the Flask API
cd backend
source venv/bin/activate
python3 app.py

# Terminal 2: run the training helper
cd backend
source venv/bin/activate
python3 train_library.py
```

## Configuration requirements

### 1. Environment variables

Ensure `backend/.env` defines the following values:

```bash
# DeepSeek (chat LLM)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
LLM_PROVIDER=deepseek

# OpenAI embeddings (DeepSeek does not offer embeddings)
OPENAI_API_KEY=your_openai_api_key_here

# Vector database (overrides optional)
VECTOR_DB_PATH=./vector_db
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

Key reminders:
- When DeepSeek is the chat provider you still need an embedding provider; OpenAI is used by default.
- Update the values above if you switch to a different LLM or embedding service.

### 2. Install dependencies

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

## Training workflow

### Step 1: Prepare the documents

Confirm that the `library` directory sits at the project root and contains your PDFs:

```
CyPlanAI/
├── backend/
├── frontend-LangChain/
└── library/
    ├── NIST.AI.100-1.pdf
    ├── NIST.AI.100-2e2025.pdf
    ├── NIST.CSWP.29.pdf
    ├── implementing_ISMS_nine_step_approach_Oct_25.pdf
    └── ...
```

### Step 2: Run the trainer

Direct training (recommended):

```bash
cd backend
source venv/bin/activate
python3 train_library_direct.py
```

The script:
1. Scans every PDF in `library`.
2. Extracts text content.
3. Splits each document into ~1000 character chunks.
4. Generates embeddings for each chunk.
5. Stores them in the ChromaDB vector store.

### Step 3: Verify the result

Once the run finishes you will see a summary that includes:
- How many files succeeded or failed.
- Basic search smoke tests.
- A list of available libraries.

## Using the trained knowledge base

After training, start the runtime services and interact with the agent as usual.

### Start the services

```bash
# Terminal 1: Flask API
cd backend
source venv/bin/activate
python3 app.py

# Terminal 2: LangGraph server
cd backend
source venv/bin/activate
python3 langgraph_server.py

# Terminal 3 (optional): Frontend
cd frontend-LangChain
pnpm dev
```

### Example prompts

Try questions such as:

**NIST CSF**
- "What is the NIST Cybersecurity Framework?"
- "List the core functions defined by NIST CSF."
- "How should an organization implement NIST CSF?"

**ISO 27001**
- "What are the primary ISO 27001 controls?"
- "Outline the approach for implementing ISO 27001."
- "What does Annex A cover?"

**NIST AI RMF**
- "Summarize the main sections of the NIST AI RMF."
- "What are the core functions of the AI Risk Management Framework?"
- "How can we apply the NIST AI RMF in practice?"

**Threat intelligence**
- "Which adversarial machine learning threats should we track?"
- "Explain what data poisoning attacks look like."
- "How can teams defend against adversarial attacks?"

**Compliance**
- "Which cybersecurity compliance frameworks are most relevant?"
- "What are best practices for GRC programs?"

## How it works

1. **Vectorization** – documents are chunked and converted into embeddings.
2. **Semantic search** – incoming questions trigger a similarity search across all stored chunks.
3. **Context injection** – retrieved passages are added to the agent prompt.
4. **Response generation** – the LLM formulates an answer grounded in the retrieved evidence.

## Training output

The summary report includes:
- Number of successfully processed files.
- Total chunks generated.
- Names of available vector libraries.
- Results of the search smoke test.

All vectors live under `backend/vector_db/` by default.

## Troubleshooting

### Issue 1: `library` folder not found
Make sure the directory exists at the project root alongside `backend/`.

### Issue 2: Embedding API errors
- Confirm that the embedding API key is valid and loaded.
- When DeepSeek is selected, provide `OPENAI_API_KEY` for embeddings.

### Issue 3: PDF processing failures
- Check whether any PDFs are corrupted or password protected.
- Open the file in a reader to confirm it renders correctly.

### Issue 4: Out-of-memory errors
- Reduce `CHUNK_SIZE` in `.env`.
- Process the documents in smaller batches.

### Issue 5: Search returns nothing
- Verify the training script completed without errors.
- Confirm you are querying the correct library name.
- Try a broader search query to test connectivity.

## Manage libraries programmatically

### List available libraries
```python
from services.document_loader import DocumentLoader

loader = DocumentLoader()
print(loader.get_all_libraries())
```

### Delete a library via the API
```bash
curl -X DELETE http://localhost:8088/api/documents/libraries/cybersecurity_frameworks \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Retrain an existing library
Re-run either training script; the vector store is automatically updated.

## Next steps

After training completes:
1. Start the Flask API and LangGraph server.
2. Use the frontend or API to converse with the agent.
3. Ask questions about NIST CSF, ISO 27001, threat intelligence, and more.
4. Validate that the answers cite the expected documents.

## Need assistance?

If you run into issues:
1. Inspect the backend logs for stack traces.
2. Confirm that all API keys are loaded from `.env`.
3. Review `backend/DOCUMENT_TRAINING.md` for API details.
4. Check that the vector store directory (`backend/vector_db/`) contains data.

Good luck with your training workflow!

