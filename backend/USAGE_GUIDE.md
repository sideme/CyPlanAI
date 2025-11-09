# Usage Guide - After Training Completion

## ✅ Training Complete!

Your library documents have been successfully trained and stored in the vector database. Now you can use the AI agent to answer questions based on these documents.

## 🚀 Step 1: Start the Services

You need to run **two servers** simultaneously:

### Terminal 1: Flask API Server
```bash
cd backend
source venv/bin/activate
python3 app.py
```

The Flask API will run on `http://localhost:8088`

### Terminal 2: LangGraph Server
```bash
cd backend
source venv/bin/activate
python3 langgraph_server.py
```

The LangGraph server will run on `http://localhost:2024`

### Terminal 3: Frontend (Optional)
```bash
cd frontend-LangChain
pnpm dev
```

The frontend will run on `http://localhost:3000`

## 💬 Step 2: Use the AI Agent

Once both servers are running, the AI agent will **automatically** use your trained documents when answering questions.

### How It Works

1. **User asks a question** → AI agent receives the question
2. **Vector search** → System searches your trained documents for relevant content
3. **Context retrieval** → Relevant document chunks are retrieved
4. **AI response** → DeepSeek LLM generates answer based on retrieved documents + framework knowledge

### Example Questions You Can Ask

**About NIST CSF:**
- "What is NIST Cybersecurity Framework?"
- "What are the core functions of NIST CSF?"
- "How do I implement NIST CSF in my organization?"

**About ISO 27001:**
- "What are the main controls in ISO 27001?"
- "How do I implement ISO 27001?"
- "What does ISO 27001 Annex A contain?"

**About NIST AI RMF:**
- "What is NIST AI Risk Management Framework?"
- "What are the core functions of NIST AI RMF?"
- "How do I apply NIST AI RMF to my AI systems?"

**About Threats:**
- "What are adversarial machine learning threats?"
- "What is data poisoning attack?"
- "How to defend against adversarial attacks?"

**About Compliance:**
- "What are the best practices for cybersecurity compliance?"
- "What GRC solutions are recommended?"
- "How do I create a cybersecurity plan?"

## 🌐 Step 3: Access Methods

### Method 1: Web Frontend (Recommended)

1. Open `http://localhost:3000` in your browser
2. If prompted, enter:
   - **Deployment URL**: `http://localhost:2024`
   - **Assistant ID**: `cyplanai`
   - **LangSmith API Key**: (leave empty for local)
3. Start chatting!

### Method 2: API Directly

You can also interact with the agent via API:

```bash
# Create a thread
curl -X POST http://localhost:2024/threads \
  -H "Content-Type: application/json" \
  -d '{"config": {}}'

# Send a message
curl -X POST http://localhost:2024/threads/{thread_id}/runs \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is NIST CSF?"}],
    "config": {}
  }'
```

## 🔍 Step 4: Verify Knowledge Base is Working

### Test Search Functionality

You can test if the vector search is working:

```python
from services.document_loader import DocumentLoader
from app import create_app

app = create_app()
with app.app_context():
    loader = DocumentLoader()
    results = loader.search("NIST Cybersecurity Framework", n_results=3)
    print(f"Found {len(results)} results")
    for result in results:
        print(f"Source: {result['metadata']['source']}")
        print(f"Content: {result['content'][:200]}...")
```

### Check Knowledge Base Status

```python
from services.document_loader import DocumentLoader
from app import create_app

app = create_app()
with app.app_context():
    loader = DocumentLoader()
    libraries = loader.get_all_libraries()
    print(f"Knowledge bases: {libraries}")
```

## 📊 What Happens When You Ask a Question

1. **Question received**: "What is NIST CSF?"

2. **Vector search**: System searches your trained PDFs for "NIST CSF"
   - Finds relevant chunks from: `NIST.CSWP.29.pdf`, `NIST.AI.100-1.pdf`, etc.

3. **Context assembly**: System combines:
   - Relevant document chunks from your library
   - Framework knowledge from database (NIST CSF, ISO 27001, etc.)
   - Threat library information

4. **AI generation**: DeepSeek LLM generates answer using:
   - Retrieved document context
   - Framework knowledge
   - System prompt instructions

5. **Response**: You get an accurate answer citing sources from your documents!

## 🎯 Best Practices

### Ask Specific Questions
- ✅ Good: "What are the five core functions of NIST CSF?"
- ✅ Good: "How do I implement ISO 27001 A.8.1.1?"
- ❌ Less effective: "Tell me about cybersecurity"

### Reference Specific Documents
- ✅ Good: "Based on the NIST AI RMF document, what are the key principles?"
- ✅ Good: "What does the ISO 27001 implementation guide say about access control?"

### Combine Frameworks
- ✅ Good: "Compare NIST CSF and ISO 27001 for access control"
- ✅ Good: "How do NIST AI RMF and MITRE ATLAS relate?"

## 🛠️ Troubleshooting

### Problem: AI doesn't use my documents
**Solution**: 
- Check if vector database exists: `ls backend/vector_db/`
- Verify documents were trained: Check training output
- Check server logs for errors

### Problem: No relevant results
**Solution**:
- Try rephrasing your question
- Use more specific keywords
- Check if documents contain the information you're asking about

### Problem: Server errors
**Solution**:
- Ensure both Flask API and LangGraph server are running
- Check API keys are configured correctly
- Review server logs for detailed error messages

## 📝 Next Steps

1. ✅ **Start both servers** (Flask API + LangGraph)
2. ✅ **Open frontend** or use API directly
3. ✅ **Ask questions** about your trained documents
4. ✅ **Verify answers** cite your documents correctly

## 🎉 You're Ready!

Your AI agent is now powered by:
- ✅ Your trained library documents (NIST, ISO 27001, threats, etc.)
- ✅ DeepSeek LLM for intelligent responses
- ✅ Vector search for accurate document retrieval
- ✅ Framework knowledge base integration

**Start asking questions and see the AI agent use your documents!**

