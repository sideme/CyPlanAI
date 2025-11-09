# CyPlanAI Setup Instructions

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher and npm
- OpenAI API key (optional, but recommended for full functionality)

## Backend Setup

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
Note: If `pip` doesn't work, try `pip3` instead

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

6. Run the Flask application (Terminal 1):
```bash
python3 app.py
```
Note: On some systems, you may need to use `python3` instead of `python`

The Flask API will run on `http://localhost:8088`

7. Run the LangGraph server (Terminal 2):
```bash
python3 langgraph_server.py
```

The LangGraph server will run on `http://localhost:2024`

## Frontend Setup

1. Navigate to the frontend-LangChain directory:
```bash
cd frontend-LangChain
```

2. Install dependencies (prefer pnpm as the repo uses it):
```bash
pnpm install
# or
npm install
```

3. (Optional) Create `.env.local` file to bypass setup form:
```bash
cp .env.local.example .env.local
# Edit .env.local and set:
# NEXT_PUBLIC_API_URL=http://localhost:2024
# NEXT_PUBLIC_ASSISTANT_ID=cyplanai
```

4. Start the development server:
```bash
npm run dev
# or
pnpm dev
```

The frontend will run on `http://localhost:3000`

**Note:** The frontend uses the official [agent-chat-ui](https://github.com/langchain-ai/agent-chat-ui). If you don't set environment variables, the app will show a setup form where you can enter:
- **Deployment URL**: `http://localhost:2024`
- **Assistant/Graph ID**: `cyplanai`
- **LangSmith API Key**: (leave empty for local development)

## First Time Setup

1. The database will be automatically created when you first run the backend
2. Frameworks and prompts are automatically seeded on first run
3. Register a new user account through the frontend
4. Start creating your first cybersecurity plan!

## Default Frameworks

The system comes pre-configured with:
- NIST Cybersecurity Framework (NIST CSF)
- ISO/IEC 27001:2013
- NIST AI Risk Management Framework
- MITRE ATLAS

Each framework includes relevant prompts for planning sessions.

## API Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/frameworks` - Get all frameworks
- `POST /api/plans` - Create new plan
- `GET /api/plans` - Get user's plans
- `POST /api/responses` - Submit prompt response
- `POST /api/plans/{id}/generate-summary` - Generate plan summary
- `GET /api/plans/{id}/export` - Export plan (PDF/JSON)
- `POST /api/feedback` - Submit feedback

## Troubleshooting

### Backend Issues
- Ensure Python virtual environment is activated
- Check that `.env` file exists with required variables
- Verify database permissions if using SQLite

### Frontend Issues
- Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check that LangGraph server is running on port 2024
- Check that Flask API is running on port 8088
- Verify CORS settings in backend `config.py`
- Check browser console for connection errors

### LangGraph Server Issues
- Ensure Flask app can initialize (database access)
- Check that LLM provider is configured correctly in `.env`
- Verify all required packages are installed (langgraph, fastapi, uvicorn)
- Check server logs for detailed error messages

### OpenAI Integration
- If OpenAI API key is not configured, the system will use a fallback plan generator
- Full AI-powered plan generation requires a valid OpenAI API key
- API calls use GPT-4 Turbo model for best results

