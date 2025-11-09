# CyPlanAI - AI-Powered Cybersecurity Plan Assistant

An intelligent assistant that automates end-to-end cybersecurity plan creation by embedding leading frameworks (NIST CSF, ISO 27001, NIST AI RMF, MITRE ATLAS) using LangChain and LangGraph.

## Team: CodeRise
- Frances Marie Limlengco (180927238)
- Side Mi (169281235)
- Tuan Duong Huynh (102318243)
- Dinh Khoa Chau (174120238)

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
│   └── ...
├── frontend-LangChain/  # Next.js frontend application (agent-chat-ui)
│   ├── src/                  # Source code
│   │   ├── app/              # Next.js app directory
│   │   ├── components/       # React components
│   │   └── ...
│   └── ...
└── docs/             # Project documentation
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher and npm/pnpm
- OpenAI API key (or Anthropic/Ollama for alternative LLM providers)

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
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_secret_key_here_change_in_production
DATABASE_URL=sqlite:///cyplanai.db
FLASK_ENV=development
# LLM Provider options: openai | anthropic | ollama
LLM_PROVIDER=openai
# OpenAI config
OPENAI_MODEL=gpt-4o-mini
# Anthropic (optional)
# ANTHROPIC_API_KEY=your_anthropic_key
# ANTHROPIC_MODEL=claude-3-5-haiku-latest
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
   - Request risk assessments
   - Generate plan summaries
   - Get information about controls and threats

## Features

- **Conversational Interface**: Chat-based interaction using agent-chat-ui
- **LangGraph Agent**: Stateful agent with tool calling capabilities
- **Knowledge Base**: RAG-powered responses with framework, control, and threat information
- **Framework Support**: NIST CSF, ISO 27001, NIST AI RMF, MITRE ATLAS
- **Risk Assessment**: Automated threat analysis and scoring
- **Plan Generation**: AI-powered plan summary generation
- **Multi-LLM Support**: OpenAI, Anthropic, or Ollama

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

## License

MIT
