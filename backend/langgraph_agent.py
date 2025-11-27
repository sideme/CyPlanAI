"""
LangGraph Agent for CyPlanAI - Cybersecurity Planning Assistant
Integrates with existing database models and knowledge base
"""
import os
import logging
from typing import Annotated, TypedDict, List, Dict, Any
from typing_extensions import Literal

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool

from config import Config

logger = logging.getLogger(__name__)
from models import db, Framework, Plan, Control, Threat
from services.knowledge_base import KnowledgeBase
from services.plan_generator import generate_plan_summary

# Note: Tool functions that access database need Flask app context
# They are defined below and wrapped in @tool decorators


def get_llm():
    """Get the configured LLM based on environment variables"""
    provider = (Config.LLM_PROVIDER or 'openai').lower()
    if provider == 'openai' and Config.OPENAI_API_KEY:
        return ChatOpenAI(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            temperature=0.4
        )
    elif provider == 'anthropic' and Config.ANTHROPIC_API_KEY:
        return ChatAnthropic(
            api_key=Config.ANTHROPIC_API_KEY,
            model=Config.ANTHROPIC_MODEL,
            temperature=0.4
        )
    elif provider == 'deepseek' and Config.DEEPSEEK_API_KEY:
        # DeepSeek uses OpenAI-compatible API
        return ChatOpenAI(
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_API_BASE,
            model=Config.DEEPSEEK_MODEL,
            temperature=0.4
        )
    elif provider == 'ollama':
        return ChatOllama(
            base_url=Config.OLLAMA_BASE_URL,
            model=Config.OLLAMA_MODEL,
            temperature=0.4
        )
    elif provider == 'qwen' and Config.DASHSCOPE_API_KEY:
        return ChatOpenAI(
            api_key=Config.DASHSCOPE_API_KEY,
            base_url=Config.DASHSCOPE_BASE_URL,
            model=Config.QWEN_MODEL,
            temperature=0.4
        )
    # Fallback to OpenAI with default
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.4)


# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    plan_id: str | None


# Define tools for the agent - these need Flask app context
def extract_text_from_message(message) -> str:
    """
    Helper to extract text from a message content which can be string, list, or other types.
    Always returns a string (may be empty).
    """
    if isinstance(message.content, str):
        return message.content
    
    if isinstance(message.content, list):
        text_parts = []
        for item in message.content:
            if isinstance(item, dict):
                # Handle {"type": "text", "text": "..."}
                if item.get("type") == "text" and "text" in item:
                    text_parts.append(str(item.get("text", "")))
                # Handle other dict structures
                elif "content" in item:
                    text_parts.append(str(item.get("content", "")))
            elif isinstance(item, str):
                text_parts.append(item)
            else:
                # Fallback: convert to string
                text_parts.append(str(item))
        return " ".join(text_parts)
    
    # Fallback: convert any other type to string
    if message.content is not None:
        return str(message.content)
    
    return ""


def normalize_message(message: BaseMessage) -> BaseMessage:
    """
    Ensure message content is a plain string (required by OpenAI-compatible APIs).
    
    This is critical for DashScope API compatibility:
    - All message content must be strings, not lists or dicts
    - ToolMessage content must be non-empty strings
    - Empty content will cause 400 errors
    """
    # If content is already a string and non-empty, return as-is
    if isinstance(message.content, str) and message.content.strip():
        return message
    
    # Extract text from complex content structures
    text = extract_text_from_message(message)
    
    # Ensure text is not empty - DashScope requires non-empty content
    if not text or not text.strip():
        text = "(empty message)"
    
    # Reconstruct message with normalized content
    if isinstance(message, HumanMessage):
        return HumanMessage(content=text, additional_kwargs=message.additional_kwargs)
    if isinstance(message, AIMessage):
        # Preserve tool_calls when normalizing AIMessage
        tool_calls = getattr(message, "tool_calls", None) if hasattr(message, "tool_calls") else None
        return AIMessage(content=text, additional_kwargs=message.additional_kwargs, tool_calls=tool_calls)
    if isinstance(message, SystemMessage):
        return SystemMessage(content=text)
    if isinstance(message, ToolMessage):
        # ToolMessage requires content to be a string
        return ToolMessage(
            content=text,
            tool_call_id=message.tool_call_id,
            additional_kwargs=message.additional_kwargs
        )
    
    # Fallback: return original message
    return message


def get_framework_info_tool(framework_id: str = None) -> str:
    """Get information about a cybersecurity framework. If no framework_id is provided, returns all frameworks."""
    from app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        if framework_id:
            fw = Framework.query.get(framework_id)
            if fw:
                return f"Framework: {fw.name} ({fw.type})\nDescription: {fw.description}\nVersion: {fw.version}"
            return f"Framework with ID {framework_id} not found."
        
        frameworks = Framework.query.all()
        if not frameworks:
            return "No frameworks available."
        
        result = "Available Frameworks:\n"
        for fw in frameworks:
            result += f"- {fw.name} ({fw.type}): {fw.description or 'No description'}\n"
        return result


def search_knowledge_base_tool(query: str) -> str:
    """Search the knowledge base for cybersecurity frameworks, controls, and threats. Use this for any questions about cybersecurity standards, controls, or threats."""
    from app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        return KnowledgeBase.get_context_for_question(query)


def generate_plan_summary_tool_func(plan_id: str) -> str:
    """Generate a comprehensive summary for a cybersecurity plan. Requires a valid plan_id."""
    from app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        plan = Plan.query.get(plan_id)
        if not plan:
            return f"Plan with ID {plan_id} not found."
        
        try:
            prompts = plan.framework.prompts if plan.framework else []
            summary = generate_plan_summary(plan, prompts, plan.responses)
            plan.summary = summary
            db.session.commit()
            return f"Plan summary generated successfully. Summary length: {len(summary)} characters."
        except Exception as e:
            return f"Error generating summary: {str(e)}"


def get_risk_assessment_tool(keywords: str) -> str:
    """Assess risks based on keywords provided. Returns relevant threats and their risk scores."""
    from app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        keywords_lower = keywords.lower()
        threats = Threat.query.filter(
            (Threat.name.ilike(f'%{keywords_lower}%')) |
            (Threat.description.ilike(f'%{keywords_lower}%')) |
            (Threat.category.ilike(f'%{keywords_lower}%'))
        ).all()
        
        if not threats:
            return f"No threats found matching: {keywords}"
        
        result = "Risk Assessment Results:\n"
        for t in threats:
            score = (t.likelihood or 2) * (t.impact or 3)
            result += f"- {t.name} ({t.category}): Risk Score {score}/25 (Likelihood: {t.likelihood}/5, Impact: {t.impact}/5)\n"
            result += f"  Description: {t.description or 'N/A'}\n"
        
        return result


# Create tool instances with @tool decorator
@tool
def get_framework_info(framework_id: str = None) -> str:
    """Get information about a cybersecurity framework. If no framework_id is provided, returns all frameworks."""
    return get_framework_info_tool(framework_id)


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for cybersecurity frameworks, controls, and threats. Use this for any questions about cybersecurity standards, controls, or threats."""
    return search_knowledge_base_tool(query)


@tool
def generate_plan_summary_tool(plan_id: str) -> str:
    """Generate a comprehensive summary for a cybersecurity plan. Requires a valid plan_id."""
    return generate_plan_summary_tool_func(plan_id)


@tool
def get_risk_assessment(keywords: str) -> str:
    """Assess risks based on keywords provided. Returns relevant threats and their risk scores."""
    return get_risk_assessment_tool(keywords)


# System prompt for the agent
SYSTEM_PROMPT = """You are CyPlanAI, an expert cybersecurity planning assistant. Your role is to help users create comprehensive cybersecurity plans based on established frameworks like NIST CSF, ISO 27001, NIST AI RMF, and MITRE ATLAS.

Key capabilities:
- Answer questions about cybersecurity frameworks, controls, and threats
- Help users understand compliance requirements
- Generate plan summaries based on user responses
- Assess risks and provide recommendations
- Guide users through the planning process

Always:
- Cite specific framework controls (e.g., "ISO 27001 A.8.1.1" or "NIST CSF PR.AC-3") when mentioning them
- Use the knowledge base tools to get accurate information when needed
- Be concise, factual, and helpful
- If you don't know something, say so rather than guessing
- IMPORTANT: If you already have relevant context provided in the system message, use it directly instead of calling search_knowledge_base again. Only call tools when you need NEW information that is not already available.

Start by greeting the user and asking about their cybersecurity planning goals."""


def create_agent_node(llm):
    """Create the main agent node that processes messages"""

    def agent_node(state: AgentState):
        # Get knowledge base context for the latest user message
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        kb_context = ""
        file_ids: List[str] = []
        if user_messages:
            latest_user_msg = user_messages[-1]
            kb_context = KnowledgeBase.get_context_for_question(extract_text_from_message(latest_user_msg))
            file_ids = latest_user_msg.additional_kwargs.get("file_ids", [])

        system_text = SYSTEM_PROMPT
        if kb_context:
            system_text += f"\n\nRELEVANT KNOWLEDGE BASE CONTEXT:\n{kb_context[:1500]}"
        if file_ids:
            system_text += (
                "\n\nREFERENCE FILES:\n"
                + "\n".join(f"- fileid://{fid}" for fid in file_ids)
                + "\nUse these uploaded documents when crafting your answer."
            )

        enhanced_system = SystemMessage(content=system_text)
        user_messages_only = [
            msg for msg in state["messages"] if not isinstance(msg, SystemMessage)
        ]

        logger.debug(
            "Invoking LLM with file_ids=%s system_prompt_preview=%s",
            file_ids,
            system_text[-500:],
        )

        normalized_messages = [
            normalize_message(enhanced_system),
            *[normalize_message(msg) for msg in user_messages_only],
        ]

        llm_to_use = llm
        if file_ids:
            llm_to_use = llm.bind(extra_body={"file_ids": file_ids})

        response = llm_to_use.invoke(normalized_messages)
        return {"messages": [response]}
    
    return agent_node


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Determine whether to call tools or end"""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, route to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Check for potential infinite loops: if we've called the same tool multiple times
        # Count recent tool calls of the same type
        tool_call_names = []
        for msg in messages[-10:]:  # Check last 10 messages
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_call_names.append(tc.get("name", ""))
        
        # If we've called search_knowledge_base more than 3 times in recent messages, force end
        if tool_call_names.count("search_knowledge_base") > 3:
            logger.warning("⚠️ Detected potential infinite loop with search_knowledge_base, forcing end")
            return "end"
        
        return "tools"
    # Otherwise, end
    return "end"


def create_agent_graph(user_id: str = None, plan_id: str = None):
    """Create and return the LangGraph agent graph"""
    llm = get_llm()
    
    # Bind tools to the LLM
    tools = [
        get_framework_info,
        search_knowledge_base,
        generate_plan_summary_tool,
        get_risk_assessment
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    # Create agent node with tools
    def agent_node(state: AgentState):
        # Get knowledge base context for the latest user message
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        kb_context = ""
        file_ids: List[str] = []
        
        if user_messages:
            latest_user_msg = user_messages[-1]
            user_text = extract_text_from_message(latest_user_msg).strip()
            if user_text:
                kb_context = KnowledgeBase.get_context_for_question(user_text)
            file_ids = latest_user_msg.additional_kwargs.get("file_ids", [])
        
        # Build system message with KB context
        system_text = SYSTEM_PROMPT
        if kb_context:
            system_text += f"\n\nRELEVANT KNOWLEDGE BASE CONTEXT:\n{kb_context[:1500]}"
            system_text += "\n\nIMPORTANT: You already have relevant knowledge base context above. Only call search_knowledge_base if you need additional information that is NOT already provided in the context above."
        
        enhanced_system = SystemMessage(content=system_text)
        
        # Per official docs: file references must be in SEPARATE system messages
        # See: https://www.alibabacloud.com/help/en/model-studio/long-context-qwen-long
        file_system_messages = []
        if file_ids:
            logger.info(f"📎 Adding {len(file_ids)} file reference(s) as separate system messages")
            for fid in file_ids:
                file_system_messages.append(SystemMessage(content=f"fileid://{fid}"))
        
        user_messages_only = [
            msg for msg in state["messages"] if not isinstance(msg, SystemMessage)
        ]

        logger.debug(
            "Invoking LLM(with tools) file_ids=%s system_prompt_preview=%s",
            file_ids,
            system_text[-500:],
        )

        # Construct messages: [main_system, file_systems..., user_messages...]
        normalized_messages = [
            normalize_message(enhanced_system),
            *[normalize_message(msg) for msg in file_system_messages],
            *[normalize_message(msg) for msg in user_messages_only],
        ]
        
        # Debug: log message structure before sending to DashScope
        logger.info("📨 Messages being sent to LLM:")
        for i, msg in enumerate(normalized_messages):
            msg_type = type(msg).__name__
            content_preview = str(msg.content)[:100] if msg.content else "(empty)"
            logger.info(f"  [{i}] {msg_type}: {content_preview}...")
            if hasattr(msg, 'tool_call_id'):
                logger.info(f"      tool_call_id: {msg.tool_call_id}")
        
        llm_to_use = llm_with_tools
        if file_ids:
            llm_to_use = llm_with_tools.bind(extra_body={"file_ids": file_ids})
            logger.info(f"🔗 Binding file_ids to LLM: {file_ids}")
        
        response = llm_to_use.invoke(normalized_messages)
        logger.info(f"✅ LLM response received: {type(response).__name__}")
        
        return {"messages": [response]}
    
    # Create tool node
    tool_node = ToolNode(tools)
    
    # Build the graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")
    
    # Compile the graph
    app = workflow.compile()
    
    return app


# Create a default agent graph instance
def get_default_agent():
    """Get a default agent instance"""
    return create_agent_graph()

