"""
LangGraph FastAPI Server for CyPlanAI
Provides LangGraph API endpoints compatible with agent-chat-ui
"""
import os
import json
import logging
import hashlib
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel

from app import create_app as create_flask_app
from models import db, AgentSession, AgentMessage, ChatThread, ChatMessage
from langgraph_agent import create_agent_graph, AgentState
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app for database access
flask_app = create_flask_app()
flask_app.app_context().push()

# FastAPI app
app = FastAPI(title="CyPlanAI LangGraph Server")

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"=== Request: {request.method} {request.url.path} ===")
    logger.info(f"Query params: {dict(request.query_params)}")
    logger.info(f"Path params: {request.path_params}")
    
    try:
        response = await call_next(request)
        logger.info(f"=== Response: {response.status_code} for {request.method} {request.url.path} ===")
        return response
    except HTTPException as e:
        logger.error(f"HTTP Exception {e.status_code}: {e.detail}")
        available_routes = [r.path for r in app.routes if hasattr(r, 'path')]
        logger.error(f"Available routes: {available_routes}")
        raise
    except Exception as e:
        logger.error(f"Exception in {request.method} {request.url.path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store agent graphs per thread (in production, use proper state management)
agent_graphs: dict[str, CompiledStateGraph] = {}


class ThreadRequest(BaseModel):
    config: Optional[dict] = {}


class MessageRequest(BaseModel):
    messages: Optional[list[dict]] = None
    config: Optional[dict] = {}
    # LangGraph SDK format support
    input: Optional[dict] = None
    stream_mode: Optional[list] = None
    stream_subgraphs: Optional[bool] = None
    stream_resumable: Optional[bool] = None
    assistant_id: Optional[str] = None
    on_disconnect: Optional[str] = None


class ThreadSearchRequest(BaseModel):
    metadata: Optional[dict] = {}
    limit: Optional[int] = 100
    before: Optional[str] = None
    after: Optional[str] = None


def get_thread_id_from_config(config: dict) -> str:
    """Extract thread ID from config, or generate one"""
    if "configurable" in config and "thread_id" in config["configurable"]:
        return config["configurable"]["thread_id"]
    return "default"


@app.get("/")
async def root():
    return {"message": "CyPlanAI LangGraph Server", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/info")
async def info():
    """Server information endpoint for frontend compatibility"""
    return {
        "status": "running",
        "server": "CyPlanAI LangGraph Server",
        "version": "1.0.0"
    }


@app.post("/threads")
async def create_thread(request: ThreadRequest = None):
    """Create a new thread for conversation"""
    logger.info("create_thread called")
    thread_id = f"thread_{os.urandom(8).hex()}"
    
    # Create agent graph for this thread
    config = request.config if request else {}
    user_id = config.get("user_id")
    plan_id = config.get("plan_id")
    
    agent_graph = create_agent_graph(user_id=user_id, plan_id=plan_id)
    agent_graphs[thread_id] = agent_graph
    
    # Store in database if user_id provided
    if user_id:
        with flask_app.app_context():
            session = AgentSession(userId=user_id, planId=plan_id)
            db.session.add(session)
            db.session.commit()
            config["session_id"] = session.sessionId

        # Always ensure we have a persisted chat thread record
        chat_thread = ChatThread.query.filter_by(threadId=thread_id).first()
        if not chat_thread:
            chat_thread = ChatThread(threadId=thread_id, userId=user_id)
            db.session.add(chat_thread)
            db.session.commit()
    
    logger.info(f"Created thread: {thread_id}")
    return {
        "thread_id": thread_id,
        "config": config
    }


@app.post("/threads/search")
async def search_threads(request: ThreadSearchRequest):
    """Search for threads (LangGraph SDK compatibility)"""
    logger.info(f"search_threads called with metadata: {request.metadata}, limit: {request.limit}")
    
    # Return all threads we have in memory (for now)
    # In production, you'd query a database
    threads = []
    for thread_id in agent_graphs.keys():
        threads.append({
            "thread_id": thread_id,
            "created_at": None,  # Could track this if needed
            "metadata": {}
        })
    
    # Apply limit
    if request.limit:
        threads = threads[:request.limit]
    
    logger.info(f"Returning {len(threads)} threads")
    return threads


@app.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, request: MessageRequest):
    """Create a run (conversation turn) in a thread"""
    logger.info(f"create_run called with thread_id: {thread_id}")
    logger.info(f"Request data: input={request.input is not None}, messages={request.messages is not None}")
    if request.input:
        logger.info(f"Input keys: {list(request.input.keys()) if request.input else 'None'}")
    if request.messages:
        logger.info(f"Messages count: {len(request.messages)}")
    
    if thread_id not in agent_graphs:
        # Try to recreate from config if available
        config = request.config or {}
        user_id = config.get("user_id")
        plan_id = config.get("plan_id")
        agent_graph = create_agent_graph(user_id=user_id, plan_id=plan_id)
        agent_graphs[thread_id] = agent_graph
    
    agent_graph = agent_graphs[thread_id]
    
    # Handle LangGraph SDK format (input.messages) or simple format (messages)
    messages_data = None
    if request.input and "messages" in request.input:
        # LangGraph SDK format
        messages_data = request.input["messages"]
    elif request.messages:
        # Simple format
        messages_data = request.messages
    
    if not messages_data:
        raise HTTPException(status_code=400, detail="Messages are required in 'messages' or 'input.messages'")
    
    # Convert messages to LangChain format
    langchain_messages = []
    for msg in messages_data:
        # Handle different message formats
        if isinstance(msg, dict):
            # Format: {"role": "user", "content": "..."} or {"type": "human", "content": [...]}
            msg_type = msg.get("type") or msg.get("role", "")
            content = msg.get("content", "")
            
            # Handle content array format from LangGraph SDK
            if isinstance(content, list):
                # Extract text from content array
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                content = " ".join(text_parts) if text_parts else ""
            
            metadata = {}
            if isinstance(msg, dict) and msg.get("id"):
                metadata["client_message_id"] = str(msg.get("id"))

            if msg_type in ["user", "human"]:
                langchain_messages.append(HumanMessage(content=content, additional_kwargs=metadata))
            elif msg_type in ["assistant", "ai"]:
                langchain_messages.append(AIMessage(content=content, additional_kwargs=metadata))
    
    # Prepare state
    config = request.config or {}
    state: AgentState = {
        "messages": langchain_messages,
        "user_id": config.get("user_id", ""),
        "plan_id": config.get("plan_id")
    }
    
    # Persist or refresh chat thread metadata
    def ensure_chat_thread(user_id: str | None = None) -> ChatThread:
        thread_record = ChatThread.query.filter_by(threadId=thread_id).first()
        if thread_record is None:
            thread_record = ChatThread(threadId=thread_id, userId=user_id)
            db.session.add(thread_record)
            db.session.commit()
        elif user_id and not thread_record.userId:
            thread_record.userId = user_id
            db.session.commit()
        return thread_record

    chat_thread = ensure_chat_thread(config.get("user_id"))

    def extract_text(content: str | list | dict | None) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
        return str(content) if content is not None else ""

    # Store the latest human message before streaming starts
    last_message = langchain_messages[-1] if langchain_messages else None
    if isinstance(last_message, HumanMessage):
        human_text = extract_text(last_message.content)
        if human_text.strip():
            latest_db_message = ChatMessage.query.filter_by(
                threadId=thread_id, role="human"
            ).order_by(ChatMessage.created_at.desc()).first()
            if not latest_db_message or latest_db_message.content != human_text:
                db.session.add(ChatMessage(
                    threadId=thread_id,
                    messageId=getattr(last_message, "id", None),
                    role="human",
                    content=human_text,
                ))
                db.session.commit()

    # Stream the response
    async def stream_events():
        try:
            logger.info(f"Starting to stream response for thread {thread_id}")
            logger.info(f"User message: {langchain_messages[-1].content if langchain_messages else 'N/A'}")
            
            last_assistant_message = None
            accumulated_content = ""
            event_count = 0
            
            # Helper to convert LangChain messages into frontend format
            def format_langchain_messages(messages, existing_ids=None):
                formatted = []
                seen = set(existing_ids or [])
                for idx, msg in enumerate(messages):
                    if isinstance(msg, (AIMessage, HumanMessage)):
                        msg_type = "ai" if isinstance(msg, AIMessage) else "human"
                        content_str = ""
                        if isinstance(msg.content, str):
                            content_str = msg.content
                        elif isinstance(msg.content, list):
                            text_parts = []
                            for item in msg.content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                                else:
                                    text_parts.append(str(item))
                            content_str = " ".join(text_parts)
                        else:
                            content_str = str(msg.content)

                        msg_id = None
                        if hasattr(msg, "id") and msg.id:
                            msg_id = str(msg.id)
                        elif hasattr(msg, "additional_kwargs") and isinstance(msg.additional_kwargs, dict):
                            msg_id = str(
                                msg.additional_kwargs.get("client_message_id")
                                or msg.additional_kwargs.get("id", "")
                            )

                        if not msg_id or msg_id in seen:
                            content_hash = hashlib.md5((content_str + msg_type + str(idx)).encode()).hexdigest()[:12]
                            msg_id = f"{msg_type}-{content_hash}"
                            counter = 0
                            while msg_id in seen:
                                counter += 1
                                msg_id = f"{msg_type}-{content_hash}-{counter}"

                        seen.add(msg_id)
                        formatted.append({
                            "id": msg_id,
                            "type": msg_type,
                            "content": [{"type": "text", "text": content_str}],
                        })
                return formatted

            all_messages_seen: list[dict] = []  # Track all messages we've seen to ensure completeness
            async for state_update in agent_graph.astream(
                state, 
                config={"configurable": {"thread_id": thread_id}},
                stream_mode=["values", "updates"]
            ):
                event_count += 1
                mode = None
                payload = state_update
                if isinstance(state_update, tuple) and len(state_update) == 2:
                    mode, payload = state_update

                mode_label = mode or "unknown"

                formatted_state = {}
                raw_messages = None

                if isinstance(payload, dict):
                    if isinstance(payload.get("messages"), list):
                        raw_messages = payload["messages"]
                    elif isinstance(payload.get("agent"), dict) and isinstance(payload["agent"].get("messages"), list):
                        raw_messages = payload["agent"]["messages"]

                    # Capture simple scalar fields only
                    if isinstance(payload.get("user_id"), str):
                        formatted_state["user_id"] = payload["user_id"]
                    if "plan_id" in payload:
                        formatted_state["plan_id"] = payload["plan_id"]

                if raw_messages is not None:
                    existing_ids = [msg.get("id") for msg in all_messages_seen if isinstance(msg, dict) and msg.get("id")]
                    formatted_messages = format_langchain_messages(raw_messages, existing_ids)

                    if mode == "values" or not all_messages_seen:
                        all_messages_seen = formatted_messages.copy()
                    else:
                        id_to_index = {msg.get("id"): idx for idx, msg in enumerate(all_messages_seen) if isinstance(msg, dict) and msg.get("id")}
                        for new_msg in formatted_messages:
                            msg_id = new_msg.get("id")
                            if msg_id in id_to_index:
                                all_messages_seen[id_to_index[msg_id]] = new_msg
                            else:
                                all_messages_seen.append(new_msg)

                    formatted_state["messages"] = all_messages_seen.copy()

                    for raw_msg in reversed(raw_messages):
                        if isinstance(raw_msg, AIMessage):
                            if isinstance(raw_msg.content, str):
                                accumulated_content = raw_msg.content
                            elif isinstance(raw_msg.content, list):
                                text_parts = [
                                    item.get("text", "")
                                    for item in raw_msg.content
                                    if isinstance(item, dict) and item.get("type") == "text"
                                ]
                                accumulated_content = " ".join(text_parts)
                            else:
                                accumulated_content = str(raw_msg.content)
                            last_assistant_message = raw_msg
                            break
                else:
                    if all_messages_seen:
                        formatted_state["messages"] = all_messages_seen.copy()

                if "messages" not in formatted_state or not formatted_state.get("messages"):
                    continue

                if "user_id" not in formatted_state:
                    formatted_state["user_id"] = state.get("user_id", "")
                if "plan_id" not in formatted_state:
                    formatted_state["plan_id"] = state.get("plan_id")

                yield {
                    "event": mode_label if mode_label in {"values", "updates"} else "data",
                    "data": {
                        mode_label if mode_label in {"values", "updates"} else "values": formatted_state
                    }
                }
 
            # Get final state to ensure we have the complete response
            if not accumulated_content or last_assistant_message is None:
                logger.warning("No content accumulated, calling ainvoke to get final state...")
                final_state = await agent_graph.ainvoke(state, config={"configurable": {"thread_id": thread_id}})
 
                # Find last AI message
                for msg in reversed(final_state.get("messages", [])):
                    if isinstance(msg, AIMessage):
                        content_str = str(msg.content) if hasattr(msg, 'content') and msg.content else ""
                        last_assistant_message = msg
                        accumulated_content = content_str
                        break
 
                if last_assistant_message is None:
                    logger.error("❌ No AIMessage found in final state!")
                    # Log all message types
                    for i, msg in enumerate(final_state.get("messages", [])):
                        logger.error(f"  Message {i}: {type(msg).__name__}")

                # Ensure we send the final formatted messages
                final_formatted_messages = format_langchain_messages(final_state.get("messages", []))
                if final_formatted_messages:
                    all_messages_seen = final_formatted_messages
                    yield {
                        "event": "values",
                        "data": {
                            "values": {
                                "messages": final_formatted_messages,
                                "user_id": state.get("user_id", ""),
                                "plan_id": state.get("plan_id"),
                            }
                        }
                    }
 
            # Save messages to database if session_id is available
            session_id = config.get("session_id")
            if session_id:
                with flask_app.app_context():
                    # Save user message
                    user_msg = langchain_messages[-1] if langchain_messages else None
                    if user_msg and isinstance(user_msg, HumanMessage):
                        agent_msg = AgentMessage(
                            sessionId=session_id,
                            role="user",
                            content=user_msg.content
                        )
                        db.session.add(agent_msg)
                    
                    # Save assistant message
                    if last_assistant_message and isinstance(last_assistant_message, AIMessage):
                        content = last_assistant_message.content
                        if isinstance(content, str) and content:
                            agent_msg = AgentMessage(
                                sessionId=session_id,
                                role="assistant",
                                content=content
                            )
                            db.session.add(agent_msg)
                    
                    db.session.commit()

            # Persist assistant reply for thread history
            if last_assistant_message and isinstance(last_assistant_message, AIMessage):
                assistant_text = extract_text(last_assistant_message.content)
                if assistant_text.strip():
                    latest_ai_message = ChatMessage.query.filter_by(
                        threadId=thread_id, role="ai"
                    ).order_by(ChatMessage.created_at.desc()).first()
                    if not latest_ai_message or latest_ai_message.content != assistant_text:
                        db.session.add(ChatMessage(
                            threadId=thread_id,
                            messageId=getattr(last_assistant_message, "id", None),
                            role="ai",
                            content=assistant_text,
                        ))
                        db.session.commit()
            
            # Send final event
            if last_assistant_message and isinstance(last_assistant_message, AIMessage):
                content = last_assistant_message.content
                if isinstance(content, str):
                    logger.info(f"✅ Sending final event to frontend")
                    logger.info(f"Final content length: {len(content)} chars")
                    logger.info(f"Final content preview: {content[:300]}...")
            yield {
                "event": "end",
                "data": {}
            }
        except Exception as e:
            import traceback
            logger.error(f"Exception in stream_events: {str(e)}")
            traceback.print_exc()
            yield {
                "event": "error",
                "data": {
                    "error": str(e)
                }
            }
    
    from fastapi.responses import StreamingResponse
    
    async def generate():
        async for event in stream_events():
            # LangGraph SDK expects SSE format: event: <event_name>\n data: <json>\n\n
            event_name = event.get("event", "data")
            event_data = event.get("data", {})
            
            # Format as proper SSE
            event_json_str = json.dumps(event_data)
            sse_message = f"event: {event_name}\ndata: {event_json_str}\n\n"

            logger.info(f"Sending SSE: event={event_name}, data length={len(event_json_str)}")
            logger.debug(f"SSE Raw Message:\n{sse_message}")
            
            yield sse_message
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/threads/{thread_id}/runs/stream")
async def create_run_stream(thread_id: str, request: MessageRequest):
    """Create a run with streaming response (alternative endpoint for frontend compatibility)"""
    logger.info(f"create_run_stream called with thread_id: {thread_id}")
    # This endpoint is the same as /runs but with /stream suffix for frontend compatibility
    return await create_run(thread_id, request)


@app.post("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str, request: Optional[dict] = None):
    """Get thread history/state (LangGraph SDK compatibility)
    
    Returns an array of checkpoints, each containing the state at that point.
    """
    logger.info(f"get_thread_history called with thread_id: {thread_id}")

    with flask_app.app_context():
        chat_thread = ChatThread.query.filter_by(threadId=thread_id).first()
        if not chat_thread:
            logger.warning(f"Thread {thread_id} not found in database")
            return []

        messages: list[ChatMessage] = ChatMessage.query.filter_by(threadId=thread_id).order_by(ChatMessage.created_at.asc()).all()

    formatted_messages = []
    for msg in messages:
        text_content = msg.content or ""
        formatted_messages.append({
            "id": msg.messageId or str(msg.id),
            "type": "human" if msg.role == "human" else "ai",
            "content": [
                {
                    "type": "text",
                    "text": text_content,
                }
            ],
        })

    if not formatted_messages:
        return []

    return [
        {
            "values": {"messages": formatted_messages},
            "next": None,
        }
    ]


@app.get("/assistants/{assistant_id}")
async def get_assistant(assistant_id: str):
    """Get assistant information"""
    logger.info(f"get_assistant called with assistant_id: {assistant_id}")
    return {
        "assistant_id": assistant_id,
        "name": "CyPlanAI",
        "description": "Cybersecurity Planning Assistant"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2024)

