# Environment Variables Setup

## For Local Development

Create a `.env.local` file in the `frontend-LangChain` directory with:

```bash
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=cyplanai
```

## Quick Setup

```bash
cd frontend-LangChain
echo "NEXT_PUBLIC_API_URL=http://localhost:2024" > .env.local
echo "NEXT_PUBLIC_ASSISTANT_ID=cyplanai" >> .env.local
```

This will bypass the setup form and connect directly to your local LangGraph server.

## For Production

If using API passthrough:

```bash
NEXT_PUBLIC_API_URL=https://your-website.com/api
NEXT_PUBLIC_ASSISTANT_ID=cyplanai
LANGGRAPH_API_URL=https://your-langgraph-server.com
LANGSMITH_API_KEY=lsv2_...
```

