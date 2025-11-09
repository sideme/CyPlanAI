# CyPlanAI Frontend (Agent Chat UI)

This is the frontend application for CyPlanAI, built using the official [agent-chat-ui](https://github.com/langchain-ai/agent-chat-ui) template.

## Setup

1. Install dependencies:
```bash
pnpm install
# or
npm install
```

2. (Optional) Create `.env.local` file to bypass setup form:
```bash
cp .env.local.example .env.local
# Then edit .env.local with your values:
# NEXT_PUBLIC_API_URL=http://localhost:2024
# NEXT_PUBLIC_ASSISTANT_ID=cyplanai
```

3. Run the development server:
```bash
pnpm dev
# or
npm run dev
```

The app will be available at `http://localhost:3000`.

## Configuration

### Environment Variables

- `NEXT_PUBLIC_API_URL`: URL of the LangGraph server (default: `http://localhost:2024`)
- `NEXT_PUBLIC_ASSISTANT_ID`: Assistant ID to use (default: `cyplanai`)
- `LANGGRAPH_API_URL`: (For API passthrough) URL of the LangGraph server
- `LANGSMITH_API_KEY`: (Optional) LangSmith API key for authentication

If environment variables are not set, the app will show a setup form on first load where you can enter:
- **Deployment URL**: `http://localhost:2024`
- **Assistant/Graph ID**: `cyplanai`
- **LangSmith API Key**: (leave empty for local development)

## Features

- Chat interface compatible with LangGraph agents
- Streaming responses from LangGraph server
- Tool visualization and state inspection
- Setup form for configuring API connection
- Modern UI with Tailwind CSS

## Development

Make sure the LangGraph server is running on `http://localhost:2024` before starting the frontend:

```bash
# Terminal 1: Flask API
cd backend
python3 app.py

# Terminal 2: LangGraph Server
cd backend
python3 langgraph_server.py

# Terminal 3: Frontend
cd frontend-LangChain
pnpm dev
```

## Production

For production deployment, see the [agent-chat-ui documentation](https://github.com/langchain-ai/agent-chat-ui#going-to-production) on setting up API passthrough or custom authentication.

## Original Agent Chat UI

This project is based on [agent-chat-ui](https://github.com/langchain-ai/agent-chat-ui) by LangChain AI.
