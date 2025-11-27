# CyPlanAI - AI-Powered Cybersecurity Plan Assistant

An intelligent assistant that automates end-to-end cybersecurity plan creation by embedding leading frameworks (NIST CSF, ISO 27001, NIST AI RMF, MITRE ATLAS) using LangChain and LangGraph.


## Architecture

### Components
- **Frontend**: Next.js application using agent-chat-ui pattern for conversational interface
- **LangGraph Agent Server**: FastAPI server providing LangGraph-compatible API endpoints
- **Backend API**: Flask REST API for user management, plans, and data persistence
- **Knowledge Base**: Formalized controls from NIST CSF, ISO 27001, NIST AI RMF, MITRE ATLAS
- **LangChain Integration**: LLM-powered agent with tools for framework queries, risk assessment, and plan generation
- **Database**: SQLite database for user data, plans, frameworks, controls, and threats

## Project Structure

```
CyPlanAI/
├── backend/          # Flask API server + LangGraph agent server
│   ├── langgraph_agent.py    # LangGraph agent definition
│   ├── langgraph_server.py   # FastAPI server for LangGraph
│   ├── app.py                # Flask application
│   ├── services/             # Backend services
│   │   ├── knowledge_base.py # RAG knowledge base service
│   │   ├── qwen_service.py   # Qwen file upload service
│   │   └── ...
│   └── ...
├── frontend-LangChain/  # Next.js frontend application (agent-chat-ui)
│   ├── src/                  # Source code
│   │   ├── app/              # Next.js app directory
│   │   ├── components/       # React components
│   │   └── ...
│   └── ...
├── library/          # Reference documents for knowledge base
│   ├── NIST.AI.100-1.pdf
│   ├── NIST.CSWP.29.pdf
│   └── ...           # PDF documents for training
└── docs/             # Project documentation
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher and npm/pnpm
- API key for at least one LLM provider:
  - OpenAI API key (for OpenAI models or embeddings)
  - Anthropic API key (for Claude models)
  - DeepSeek API key (for DeepSeek models)
  - DashScope API key (for Qwen models and document upload)
  - Or use Ollama for local models

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python3 -m venv venv
```

3. Activate the virtual environment:
- On macOS/Linux:
```bash
source venv/bin/activate
```
- On Windows:
```bash
venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create a `.env` file in the backend directory:
```bash
SECRET_KEY=your_secret_key_here_change_in_production
DATABASE_URL=sqlite:///cyplanai.db
FLASK_ENV=development

# LLM Provider options: openai | anthropic | ollama | deepseek | qwen
LLM_PROVIDER=openai

# OpenAI config
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Anthropic (optional)
# ANTHROPIC_API_KEY=your_anthropic_key
# ANTHROPIC_MODEL=claude-3-5-haiku-latest

# DeepSeek (optional)
# DEEPSEEK_API_KEY=your_deepseek_api_key
# DEEPSEEK_API_BASE=https://api.deepseek.com
# DEEPSEEK_MODEL=deepseek-chat
# Note: DeepSeek doesn't provide embeddings, set OPENAI_API_KEY for embeddings

# Qwen/DashScope (optional, required for document upload feature)
# DASHSCOPE_API_KEY=your_dashscope_api_key
# DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# QWEN_MODEL=qwen-long

# Ollama local (optional)
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.1

# CORS (dev): allow both localhost and 127.0.0.1
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

6. Initialize the database (runs automatically on first start):
```bash
python3 app.py
```

7. Run the LangGraph server (in a separate terminal):
```bash
python3 langgraph_server.py
```

The LangGraph server will run on `http://localhost:2024`
The Flask API will run on `http://localhost:8088`

### Frontend Setup

1. Navigate to the frontend-LangChain directory:
```bash
cd frontend-LangChain
```

2. Install dependencies (prefer pnpm):
```bash
pnpm install
# or
npm install
```

3. (Optional) Create `.env.local` file to bypass setup form:
```bash
cp .env.local.example .env.local
# Edit .env.local with your values
```

4. Start the development server:
```bash
pnpm dev
# or
npm run dev
```

The frontend will run on `http://localhost:3000`

## Usage

1. **Start the backend services:**
   - Run Flask API: `cd backend && python3 app.py`
   - Run LangGraph server: `cd backend && python3 langgraph_server.py`

2. **Start the frontend:**
   - Run Next.js: `cd frontend && npm run dev`

3. **Access the application:**
   - Open `http://localhost:3000` in your browser
   - If environment variables are not set, you'll see a setup form:
     - Enter LangGraph API URL: `http://localhost:2024`
     - Enter Assistant ID: `cyplanai`
     - Optionally enter LangSmith API key if using deployed server
   - Click "Continue" to start chatting with CyPlanAI

4. **Chat with CyPlanAI:**
   - Ask questions about cybersecurity frameworks
   - Upload PDF documents for AI to analyze (requires Qwen provider)
   - Request risk assessments
   - Generate plan summaries
   - Get information about controls and threats

5. **Train Knowledge Base (Optional):**
   - Place PDF documents in the `library/` folder
   - Run training script: `cd backend && python3 train_library_direct.py`
   - See `backend/TRAIN_LIBRARY_GUIDE.md` for detailed instructions

## Features

- **Conversational Interface**: Chat-based interaction using agent-chat-ui
- **LangGraph Agent**: Stateful agent with tool calling capabilities
- **Knowledge Base**: RAG-powered responses with framework, control, and threat information
- **Document Upload**: Upload PDF/DOCX files for AI analysis (Qwen-Long model)
- **Framework Support**: NIST CSF, ISO 27001, NIST AI RMF, MITRE ATLAS
- **Risk Assessment**: Automated threat analysis and scoring
- **Plan Generation**: AI-powered plan summary generation
- **Multi-LLM Support**: OpenAI, Anthropic, DeepSeek, Qwen, or Ollama
- **Knowledge Base Training**: Train custom knowledge base from PDF documents

## API Endpoints

### LangGraph Server (Port 2024)
- `GET /` - Server status
- `GET /health` - Health check
- `POST /threads` - Create new conversation thread
- `POST /threads/{thread_id}/runs` - Send message and get streaming response
- `GET /assistants/{assistant_id}` - Get assistant information

### Flask API (Port 8088)
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/frameworks` - Get all frameworks
- `POST /api/plans` - Create new plan
- `GET /api/plans` - Get user's plans
- `POST /api/responses` - Submit prompt response
- `POST /api/plans/{id}/generate-summary` - Generate plan summary
- `GET /api/plans/{id}/export` - Export plan (PDF/JSON)
- `POST /api/feedback` - Submit feedback
- `POST /api/documents/upload` - Upload document to knowledge base
- `GET /api/documents/libraries` - Get all document libraries

## Development

### Running Both Servers

For development, you'll need to run both the Flask API and LangGraph server:

**Terminal 1 (Flask API):**
```bash
cd backend
source venv/bin/activate
python3 app.py
```

**Terminal 2 (LangGraph Server):**
```bash
cd backend
source venv/bin/activate
python3 langgraph_server.py
```

**Terminal 3 (Frontend):**
```bash
cd frontend-LangChain
pnpm dev
```

### Knowledge Base Training

To train the knowledge base with your own documents:

1. Place PDF documents in the `library/` folder at the project root
2. Run the training script:
```bash
cd backend
source venv/bin/activate
python3 train_library_direct.py
```

For detailed instructions, see `backend/TRAIN_LIBRARY_GUIDE.md`

### Document Upload Feature

The system supports uploading PDF/DOCX files for AI analysis:

1. **Requirements**: Use Qwen as LLM provider with DashScope API
2. **Configuration**: Set `LLM_PROVIDER=qwen` and `DASHSCOPE_API_KEY` in `.env`
3. **Usage**: Click "Upload files" button in the chat interface
4. **Supported formats**: PDF (up to 150MB), DOCX, TXT, and more

For detailed documentation, see `backend/PDF_UPLOAD_GUIDE.md`

## Project Management

### Sprint Planning and Backlog Tracking

Sprint planning and backlog management were conducted using Microsoft Project. Tasks were organized into functional phases including System Design, Development and Testing, QA, and Presentation Prep. Each task includes assigned team members, start and end dates, durations, and dependencies. The Gantt chart illustrates our sprint timeline and progress, with all tasks completed by November 27, 2025. Daily standups ensured updates were reflected in MS Project, supporting a successful demo and final milestone submission.

## Troubleshooting

### Backend Issues
- Ensure Python virtual environment is activated
- Check that `.env` file exists with required variables
- Verify database permissions if using SQLite
- Make sure both Flask API and LangGraph server are running

### Frontend Issues
- Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check that LangGraph server is running on port 2024
- Verify CORS settings in backend configuration
- Check browser console for connection errors

### LangGraph Server Issues
- Ensure Flask app can initialize (database access)
- Check that LLM provider is configured correctly
- Verify all required packages are installed
- Check server logs for detailed error messages

### Document Upload Issues
- Ensure `LLM_PROVIDER=qwen` is set for document upload feature
- Verify `DASHSCOPE_API_KEY` is configured correctly
- Check file size limits (PDF: 150MB, Images: 20MB)
- See `backend/PDF_UPLOAD_GUIDE.md` for troubleshooting

### Knowledge Base Issues
- Ensure documents are placed in `library/` folder
- Verify OpenAI API key is set (required for embeddings)
- Check training logs for errors
- See `backend/TRAIN_LIBRARY_GUIDE.md` for detailed help

## License

MIT
