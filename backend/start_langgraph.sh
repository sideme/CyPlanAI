#!/bin/bash
# Start script for LangGraph server

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the LangGraph server
python3 langgraph_server.py

