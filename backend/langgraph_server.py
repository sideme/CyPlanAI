"""
LangGraph FastAPI Server for CyPlanAI
Provides LangGraph API endpoints compatible with agent-chat-ui
"""
import os
import json
import logging
import hashlib
import io
import base64
from datetime import datetime
from typing import Optional

import jwt
from jwt import InvalidTokenError, ExpiredSignatureError

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from pydantic import BaseModel

from app import create_app as create_flask_app
from models import db, AgentSession, AgentMessage, ChatThread, ChatMessage, User
from langgraph_agent import (
    create_agent_graph,
    AgentState,
    get_llm,
    extract_text_from_message,
)
from services.qwen_service import QwenFileService
from config import Config
from services.title_generator import generate_conversation_title

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app for database access
flask_app = create_flask_app()
flask_app.app_context().push()

SUPPORTED_FILE_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def generate_summary_from_tool_context(question: str, tool_context: str) -> Optional[str]:
    """
    When the agent gets stuck returning tool calls without text, fall back to a direct LLM
    call that summarizes the retrieved tool context for the user.
    """
    if not question.strip() or not tool_context.strip():
        return None

    try:
        llm = get_llm()
        system_prompt = (
            "You are CyPlanAI fallback summarizer. The user question and the context "
            "retrieved from internal tools are provided. Craft a clear, actionable response "
            "using only the supplied context. Do not mention tool calls or that this is a fallback."
        )
        human_prompt = (
            f"User question:\n{question.strip()}\n\n"
            f"Context retrieved from tools:\n{tool_context.strip()}\n\n"
            "Provide a concise, helpful answer referencing the context above. "
            "If the context is insufficient, clearly state what additional details are needed."
        )
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]
        )
        if not response:
            return None

        summary_text = extract_text_from_message(response)
        return summary_text.strip() if summary_text else None
    except Exception as exc:
        logger.error("Fallback summary generation failed: %s", exc)
        return None

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


class ThreadUpdateRequest(BaseModel):
    title: Optional[str] = None


class ThreadDeleteRequest(BaseModel):
    hard_delete: Optional[bool] = False


def _extract_token(authorization: Optional[str], x_api_key: Optional[str]) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    if x_api_key:
        return x_api_key.strip()
    return None


async def get_authenticated_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> User:
    token = _extract_token(authorization, x_api_key)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        payload = jwt.decode(
            token,
            flask_app.config["JWT_SECRET_KEY"],
            algorithms=[flask_app.config.get("JWT_ALGORITHM", "HS256")],
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = User.query.get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_thread_id_from_config(config: dict) -> str:
    """Extract thread ID from config, or generate one"""
    if "configurable" in config and "thread_id" in config["configurable"]:
        return config["configurable"]["thread_id"]
    return "default"


def _format_chat_messages(messages: list[ChatMessage]) -> list[dict]:
    formatted: list[dict] = []
    for msg in messages:
        text_content = msg.content or ""
        formatted.append(
            {
                "id": msg.messageId or str(msg.id),
                "type": "human" if msg.role == "human" else "ai",
                "content": [
                    {
                        "type": "text",
                        "text": text_content,
                    }
                ],
            }
        )
    return formatted


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
async def create_thread(request: ThreadRequest = None, user: User = Depends(get_authenticated_user)):
    """Create a new thread for conversation"""
    logger.info("create_thread called")
    thread_id = f"thread_{os.urandom(8).hex()}"
    
    # Create agent graph for this thread
    config = dict(request.config) if request and request.config else {}
    user_id = user.userId
    plan_id = config.get("plan_id")
    config["user_id"] = user_id
    
    agent_graph = create_agent_graph(user_id=user_id, plan_id=plan_id)
    agent_graphs[thread_id] = agent_graph
    
    # Store in database if user_id provided
    with flask_app.app_context():
        session = AgentSession(userId=user_id, planId=plan_id)
        db.session.add(session)
        db.session.commit()
        config["session_id"] = session.sessionId

        # Always ensure we have a persisted chat thread record
        chat_thread = ChatThread.query.filter_by(threadId=thread_id).first()
        if chat_thread and chat_thread.userId and chat_thread.userId != user_id:
            raise HTTPException(status_code=403, detail="Thread already exists for another user")
        if not chat_thread:
            chat_thread = ChatThread(threadId=thread_id, userId=user_id, last_message_at=datetime.utcnow())
            db.session.add(chat_thread)
            db.session.commit()
        elif not chat_thread.userId:
            chat_thread.userId = user_id
            db.session.commit()
        else:
            # Ensure last_message_at is set even on reused threads
            if not chat_thread.last_message_at:
                chat_thread.last_message_at = chat_thread.updated_at or chat_thread.created_at
                db.session.commit()

        metadata = {
            "title": chat_thread.title,
            "auto_title": chat_thread.auto_title,
            "last_message_at": chat_thread.last_message_at.isoformat() if chat_thread.last_message_at else None,
        }
    
    # Outside app context, rely on captured metadata dict to avoid detached instance usage.

    logger.info(f"Created thread: {thread_id}")
    return {
        "thread_id": thread_id,
        "config": config,
        "metadata": metadata,
    }


@app.post("/threads/search")
async def search_threads(request: ThreadSearchRequest, user: User = Depends(get_authenticated_user)):
    """Search for threads (LangGraph SDK compatibility)"""
    logger.info(f"search_threads called with metadata: {request.metadata}, limit: {request.limit}")

    limit = max(1, min(request.limit or 100, 100))

    query = (
        ChatThread.query.filter_by(userId=user.userId)
        .order_by(ChatThread.last_message_at.desc().nullslast(), ChatThread.updated_at.desc())
        .limit(limit)
    )

    threads = []
    for thread in query.all():
        messages = (
            ChatMessage.query.filter_by(threadId=thread.threadId)
            .order_by(ChatMessage.created_at.asc())
            .limit(5)
            .all()
        )
        formatted_messages = _format_chat_messages(messages)
        threads.append(
            {
                "thread_id": thread.threadId,
                "created_at": thread.created_at.isoformat() if thread.created_at else None,
                "metadata": {
                    "title": thread.title,
                    "auto_title": thread.auto_title,
                    "last_message_at": thread.last_message_at.isoformat() if thread.last_message_at else None,
                },
                "values": {"messages": formatted_messages} if formatted_messages else {},
            }
        )

    logger.info(f"Returning {len(threads)} threads")
    return threads


@app.patch("/threads/{thread_id}")
async def update_thread(thread_id: str, request: ThreadUpdateRequest, user: User = Depends(get_authenticated_user)):
    """Update thread metadata such as the display title."""
    chat_thread = ChatThread.query.filter_by(threadId=thread_id).first()
    if not chat_thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if chat_thread.userId and chat_thread.userId != user.userId:
        raise HTTPException(status_code=403, detail="Thread belongs to a different user")

    new_title = (request.title or "").strip()
    chat_thread.title = new_title or None
    chat_thread.updated_at = datetime.utcnow()
    db.session.commit()

    return {
        "thread_id": thread_id,
        "metadata": {
            "title": chat_thread.title,
            "auto_title": chat_thread.auto_title,
            "last_message_at": chat_thread.last_message_at.isoformat() if chat_thread.last_message_at else None,
        },
    }

@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str, user: User = Depends(get_authenticated_user)):
    """Delete a thread and its messages for the current user."""
    chat_thread = ChatThread.query.filter_by(threadId=thread_id).first()
    if not chat_thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if chat_thread.userId and chat_thread.userId != user.userId:
        raise HTTPException(status_code=403, detail="Thread belongs to a different user")

    ChatMessage.query.filter_by(threadId=thread_id).delete()
    db.session.delete(chat_thread)
    db.session.commit()

    agent_graphs.pop(thread_id, None)

    return {"thread_id": thread_id, "deleted": True}


@app.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, request: MessageRequest, user: User = Depends(get_authenticated_user)):
    """Create a run (conversation turn) in a thread"""
    logger.info(f"create_run called with thread_id: {thread_id}")
    logger.info(f"Request data: input={request.input is not None}, messages={request.messages is not None}")
    if request.input:
        logger.info(f"Input keys: {list(request.input.keys()) if request.input else 'None'}")
    if request.messages:
        logger.info(f"Messages count: {len(request.messages)}")
    
    config = dict(request.config) if request.config else {}
    config["user_id"] = user.userId
    plan_id = config.get("plan_id")

    chat_thread = ChatThread.query.filter_by(threadId=thread_id).first()
    if chat_thread:
        if chat_thread.userId and chat_thread.userId != user.userId:
            raise HTTPException(status_code=403, detail="Thread belongs to a different user")
        if not chat_thread.userId:
            chat_thread.userId = user.userId
            db.session.commit()
    else:
        # Auto-create thread if it doesn't exist (e.g., when SDK creates thread on first submit)
        logger.info(f"Thread {thread_id} not found, auto-creating...")
        chat_thread = ChatThread(threadId=thread_id, userId=user.userId, last_message_at=datetime.utcnow())
        db.session.add(chat_thread)
        db.session.commit()
    
    if thread_id not in agent_graphs:
        # Create agent graph for this thread (auto-created or existing)
        logger.info(f"Creating agent graph for thread {thread_id}")
        agent_graph = create_agent_graph(user_id=user.userId, plan_id=plan_id)
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

            metadata = {}
            if msg.get("id"):
                metadata["client_message_id"] = str(msg.get("id"))
            uploaded_file_ids: list[str] = []

            # Handle content array format from LangGraph SDK
            if isinstance(content, list):
                processed_content = []
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    
                    item_type = item.get("type")
                    
                    if item_type == "text":
                        processed_content.append({
                            "type": "text", 
                            "text": item.get("text", "")
                        })
                    elif item_type == "image":
                        # Convert frontend image to LangChain image_url
                        # This allows multimodal models to see the image
                        mime = item.get("mime_type", "image/jpeg")
                        data = item.get("data", "")
                        processed_content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data}"}
                        })
                    elif (
                        item_type == "file"
                        and item.get("mime_type") in SUPPORTED_FILE_MIME_TYPES
                    ):
                        mime_type = item.get("mime_type")
                        try:
                            data = item.get("data", "")
                            file_bytes = base64.b64decode(data)
                            filename = item.get("metadata", {}).get(
                                "filename",
                                f"uploaded{SUPPORTED_FILE_MIME_TYPES[mime_type]}",
                            )
                            
                            # Special handling for Qwen: Upload to DashScope
                            llm_provider = Config.LLM_PROVIDER.lower()
                            
                            if llm_provider == 'qwen':
                                logger.info(f"📤 Uploading {filename} to DashScope for Qwen-Long...")
                                file_id = QwenFileService.upload_file(file_bytes, filename)
                                
                                if file_id:
                                    logger.info(f"✅ File uploaded successfully: {file_id}")
                                    uploaded_file_ids.append(file_id)
                                    
                                    # Don't add anything to processed_content for files
                                    # Frontend already has file preview from optimistic message
                                    # Backend only needs to store file_id in metadata for agent
                                    
                                    logger.info(f"📄 File ID stored in metadata. Agent will reference it in system message.")
                                else:
                                    logger.error("❌ Qwen upload failed")
                                    processed_content.append({
                                        "type": "text",
                                        "text": f"\n[Error: Failed to upload file {filename} ({mime_type}) to Qwen service]\n"
                                    })
                            else:
                                # For other providers (DeepSeek/OpenAI) that don't support native document upload
                                logger.warning(f"⚠️  Native file upload not supported for provider: {llm_provider}")
                                # Add a warning message
                                processed_content.append({
                                    "type": "text",
                                    "text": (
                                        f"\n[Warning: File {filename} ({mime_type}) cannot be processed. "
                                        f"Current model provider ({llm_provider}) does not support direct document upload. "
                                        "Please use Qwen-Long for document support.]\n"
                                    ),
                                })

                        except Exception as e:
                            logger.error(f"❌ Error processing PDF: {str(e)}")
                            import traceback
                            logger.error(traceback.format_exc())
                            filename = item.get("metadata", {}).get(
                                "filename",
                                f"uploaded{SUPPORTED_FILE_MIME_TYPES.get(mime_type, '')}",
                            )
                            processed_content.append({
                                "type": "text",
                                "text": f"\n\n[Error processing file {filename} ({mime_type}): {str(e)}]\n\n"
                            })
                
                # Update content to be the processed list which includes extracted text
                if processed_content:
                    content = processed_content
                else:
                    content = ""
            
            if uploaded_file_ids:
                metadata["file_ids"] = uploaded_file_ids

            if msg_type in ["user", "human"]:
                langchain_messages.append(
                    HumanMessage(content=content, additional_kwargs=metadata)
                )
            elif msg_type in ["assistant", "ai"]:
                langchain_messages.append(
                    AIMessage(content=content, additional_kwargs=metadata)
                )
    
    # Prepare state
    state: AgentState = {
        "messages": langchain_messages,
        "user_id": config.get("user_id", ""),
        "plan_id": config.get("plan_id"),
    }
    
    # Persist or refresh chat thread metadata
    def ensure_chat_thread(user_id: str) -> ChatThread:
        thread_record = ChatThread.query.filter_by(threadId=thread_id).first()
        if thread_record is None:
            thread_record = ChatThread(
                threadId=thread_id,
                userId=user_id,
                last_message_at=datetime.utcnow(),
            )
            db.session.add(thread_record)
            db.session.commit()
        elif not thread_record.userId:
            thread_record.userId = user_id
            db.session.commit()
        elif thread_record.userId != user_id:
            raise HTTPException(status_code=403, detail="Thread belongs to a different user")
        return thread_record

    chat_thread = ensure_chat_thread(user.userId)

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
    latest_human_text: Optional[str] = None
    last_message = langchain_messages[-1] if langchain_messages else None
    if isinstance(last_message, HumanMessage):
        human_text = extract_text(last_message.content)
        if human_text.strip():
            latest_human_text = human_text
            now = datetime.utcnow()
            chat_thread.last_message_at = now
            chat_thread.updated_at = now
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
                # Don't use 'seen' set - let frontend handle deduplication by ID
                # Backend should preserve original IDs, not generate new ones
                for idx, msg in enumerate(messages):
                    if isinstance(msg, (AIMessage, HumanMessage)):
                        msg_type = "ai" if isinstance(msg, AIMessage) else "human"
                        
                        formatted_content = []
                        if isinstance(msg.content, str):
                            formatted_content = [{"type": "text", "text": msg.content}]
                        elif isinstance(msg.content, list):
                            for item in msg.content:
                                if isinstance(item, dict):
                                    if item.get("type") == "text":
                                        formatted_content.append(item)
                                    elif item.get("type") == "image_url":
                                        # Try to restore base64 image for frontend
                                        url = item.get("image_url", {}).get("url", "")
                                        if url.startswith("data:"):
                                            try:
                                                # data:image/png;base64,......
                                                header, data = url.split(",", 1)
                                                mime = header.split(":")[1].split(";")[0]
                                                formatted_content.append({
                                                    "type": "image",
                                                    "source_type": "base64",
                                                    "mime_type": mime,
                                                    "data": data
                                                })
                                            except:
                                                formatted_content.append({"type": "text", "text": "[Image]"})
                                        else:
                                            formatted_content.append({"type": "text", "text": f"[Image: {url}]"})
                                    else:
                                        # Keep other types as text representation if unknown
                                        formatted_content.append({"type": "text", "text": str(item)})
                                else:
                                    formatted_content.append({"type": "text", "text": str(item)})
                        else:
                            formatted_content = [{"type": "text", "text": str(msg.content)}]

                        msg_id = None
                        if hasattr(msg, "id") and msg.id:
                            msg_id = str(msg.id)
                        elif hasattr(msg, "additional_kwargs") and isinstance(msg.additional_kwargs, dict):
                            msg_id = str(
                                msg.additional_kwargs.get("client_message_id")
                                or msg.additional_kwargs.get("id", "")
                            )

                        if not msg_id:
                            # Only generate hash ID if no ID exists at all
                            # Don't check 'seen' - preserve original IDs across multiple SSE events
                            content_str_for_hash = json.dumps(formatted_content, sort_keys=True)
                            content_hash = hashlib.md5((content_str_for_hash + msg_type + str(idx)).encode()).hexdigest()[:12]
                            msg_id = f"{msg_type}-{content_hash}"
                        if msg_type == "human":
                            logger.info(
                                "🔍 Formatting human message: id=%s has_client_id=%s content_preview=%s",
                                msg_id,
                                "client_message_id" in getattr(msg, "additional_kwargs", {}),
                                str(formatted_content)[:100],
                            )
                        formatted_msg = {
                            "id": msg_id,
                            "type": msg_type,
                            "content": formatted_content,
                        }
                        if hasattr(msg, "additional_kwargs") and isinstance(msg.additional_kwargs, dict) and msg.additional_kwargs:
                            formatted_msg["additional_kwargs"] = msg.additional_kwargs
                        # Include tool_calls for AI messages
                        if msg_type == "ai":
                            # Debug: log tool_calls availability
                            has_tool_calls_attr = hasattr(msg, "tool_calls")
                            tool_calls_value = getattr(msg, "tool_calls", None) if has_tool_calls_attr else None
                            
                            # Log tool_calls info for debugging
                            if tool_calls_value:
                                logger.info(f"🔍 AI message has tool_calls: {len(tool_calls_value) if isinstance(tool_calls_value, list) else 'non-list'}, type={type(tool_calls_value)}")
                            
                            if has_tool_calls_attr and tool_calls_value:
                                tool_calls_list = []
                                for i, tc in enumerate(tool_calls_value):
                                    # LangChain AIMessage.tool_calls is a list of dicts
                                    # Each dict has: id, name, args
                                    if isinstance(tc, dict):
                                        tool_call = {
                                            "id": tc.get("id") or f"call_{i}",
                                            "name": tc.get("name") or "",
                                            "args": tc.get("args") or {},
                                            "type": "function",
                                        }
                                    else:
                                        # Fallback for object format
                                        tool_call = {
                                            "id": getattr(tc, "id", None) or f"call_{i}",
                                            "name": getattr(tc, "name", None) or "",
                                            "args": getattr(tc, "args", None) or {},
                                            "type": "function",
                                        }
                                    tool_calls_list.append(tool_call)
                                if tool_calls_list:
                                    formatted_msg["tool_calls"] = tool_calls_list
                                    logger.info(f"📦 Including {len(tool_calls_list)} tool_calls in AI message: {[tc.get('name', 'unknown') for tc in tool_calls_list]}")
                            elif msg_type == "ai" and not tool_calls_value:
                                logger.warning(f"⚠️ AI message has no tool_calls but content is empty. Message ID: {msg_id}, content length: {len(str(formatted_content))}")
                        formatted.append(formatted_msg)
                return formatted

            all_messages_seen: list[dict] = []  # Track all messages we've seen to ensure completeness
            async for state_update in agent_graph.astream(
                state, 
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": 50  # Increase recursion limit to allow more tool calls
                },
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
                    try:
                        human_ids = [
                            (msg.get("id"), msg.get("additional_kwargs", {}).get("client_message_id"))
                            for msg in formatted_state["messages"]
                            if isinstance(msg, dict) and msg.get("type") == "human"
                        ]
                        assistant_ids = [
                            msg.get("id")
                            for msg in formatted_state["messages"]
                            if isinstance(msg, dict) and msg.get("type") == "ai"
                        ]
                        logger.info(
                            "📨 Emitting %d message(s) via SSE | human_ids=%s | assistant_ids=%s",
                            len(formatted_state["messages"]),
                            human_ids,
                            assistant_ids,
                        )
                    except Exception as log_err:
                        logger.warning("Failed to log emitted message IDs: %s", log_err)

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
                final_state_messages = list(final_state.get("messages", []))
                for msg in reversed(final_state_messages):
                    if isinstance(msg, AIMessage):
                        content_str = str(msg.content) if hasattr(msg, 'content') and msg.content else ""
                        last_assistant_message = msg
                        accumulated_content = content_str
                        break
 
                if last_assistant_message is None:
                    logger.error("❌ No AIMessage found in final state!")
                    # Log all message types
                    for i, msg in enumerate(final_state_messages):
                        logger.error(f"  Message {i}: {type(msg).__name__}")
                else:
                    logger.warning("Final AI message still has empty content; attempting fallback summary.")

                # Attempt fallback summary if needed
                if (not accumulated_content or not accumulated_content.strip()) and latest_human_text:
                    tool_context_segments = []
                    for msg in final_state_messages:
                        if isinstance(msg, ToolMessage):
                            tool_context_segments.append(extract_text_from_message(msg))
                    fallback_context = "\n\n".join(tool_context_segments[-3:])

                    fallback_summary = generate_summary_from_tool_context(latest_human_text, fallback_context)
                    fallback_text = fallback_summary
                    if not fallback_text and fallback_context.strip():
                        logger.warning("Fallback LLM summary unavailable; returning tool context directly.")
                        fallback_text = (
                            "Here is the most relevant information I retrieved from the knowledge base:\n\n"
                            + fallback_context.strip()[:2000]
                        )
                    if not fallback_text:
                        logger.warning(
                            "Fallback failed and no tool context available; sending apology message."
                        )
                        fallback_text = (
                            "I attempted to look up supporting documentation but couldn't complete the response. "
                            "Please rephrase your question or provide more details."
                        )

                    if fallback_text:
                        logger.info("✅ Injecting fallback response to replace empty AI reply.")
                        fallback_ai_message = AIMessage(content=fallback_text)
                        final_state_messages.append(fallback_ai_message)
                        last_assistant_message = fallback_ai_message
                        accumulated_content = fallback_text

                # Ensure we send the final formatted messages
                final_formatted_messages = format_langchain_messages(final_state_messages)
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
                    now = datetime.utcnow()
                    chat_thread.last_message_at = now
                    chat_thread.updated_at = now
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
                        if not chat_thread.title and not chat_thread.auto_title:
                            try:
                                chat_thread.auto_title = generate_conversation_title(
                                    latest_human_text or "",
                                    assistant_text,
                                )
                            except Exception as err:  # pragma: no cover
                                logger.warning("Failed to auto-generate title: %s", err)
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
async def create_run_stream(thread_id: str, request: MessageRequest, user: User = Depends(get_authenticated_user)):
    """Create a run with streaming response (alternative endpoint for frontend compatibility)"""
    logger.info(f"create_run_stream called with thread_id: {thread_id}")
    # This endpoint is the same as /runs but with /stream suffix for frontend compatibility
    return await create_run(thread_id=thread_id, request=request, user=user)


@app.post("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str, request: Optional[dict] = None, user: User = Depends(get_authenticated_user)):
    """Get thread history/state (LangGraph SDK compatibility)
    
    Returns an array of checkpoints, each containing the state at that point.
    """
    logger.info(f"get_thread_history called with thread_id: {thread_id}")

    with flask_app.app_context():
        chat_thread = ChatThread.query.filter_by(threadId=thread_id).first()
        if not chat_thread:
            logger.warning(f"Thread {thread_id} not found in database")
            return []
        if chat_thread.userId and chat_thread.userId != user.userId:
            raise HTTPException(status_code=403, detail="Thread belongs to a different user")
        if not chat_thread.userId:
            chat_thread.userId = user.userId
            db.session.commit()

        messages: list[ChatMessage] = ChatMessage.query.filter_by(threadId=thread_id).order_by(ChatMessage.created_at.asc()).all()

    formatted_messages = _format_chat_messages(messages)

    if not formatted_messages:
        return []

    return [
        {
            "values": {"messages": formatted_messages},
            "next": None,
        }
    ]


@app.get("/threads/{thread_id}/state")
async def get_thread_state(thread_id: str, user: User = Depends(get_authenticated_user)):
    """Return the latest state for a thread (values/messages)."""
    logger.info(f"get_thread_state called with thread_id: {thread_id}")

    with flask_app.app_context():
        chat_thread = ChatThread.query.filter_by(threadId=thread_id).first()
        if not chat_thread:
            logger.warning(f"Thread {thread_id} not found in database")
            raise HTTPException(status_code=404, detail="Thread not found")
        if chat_thread.userId and chat_thread.userId != user.userId:
            raise HTTPException(status_code=403, detail="Thread belongs to a different user")
        if not chat_thread.userId:
            chat_thread.userId = user.userId
            db.session.commit()

        messages: list[ChatMessage] = ChatMessage.query.filter_by(threadId=thread_id).order_by(ChatMessage.created_at.asc()).all()

    formatted_messages = _format_chat_messages(messages)

    return {
        "thread_id": thread_id,
        "values": {
            "messages": formatted_messages,
            "user_id": user.userId,
        },
        "metadata": {
            "title": chat_thread.title,
            "auto_title": chat_thread.auto_title,
            "last_message_at": chat_thread.last_message_at.isoformat() if chat_thread.last_message_at else None,
            "created_at": chat_thread.created_at.isoformat() if chat_thread.created_at else None,
            "updated_at": chat_thread.updated_at.isoformat() if chat_thread.updated_at else None,
        },
    }


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

