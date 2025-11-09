"""
LangGraph Agent for CyPlanAI - Cybersecurity Planning Assistant
Integrates with existing database models and knowledge base
"""
import os
from typing import Annotated, TypedDict, List, Dict, Any
from typing_extensions import Literal

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool

from config import Config
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
    # Fallback to OpenAI with default
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.4)


# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    plan_id: str | None


# Define tools for the agent - these need Flask app context
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
- Use the knowledge base tools to get accurate information
- Be concise, factual, and helpful
- If you don't know something, say so rather than guessing

Start by greeting the user and asking about their cybersecurity planning goals."""


def create_agent_node(llm):
    """Create the main agent node that processes messages"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    chain = prompt | llm
    
    def agent_node(state: AgentState):
        # Get knowledge base context for the latest user message
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        if user_messages:
            latest_user_msg = user_messages[-1].content
            kb_context = KnowledgeBase.get_context_for_question(latest_user_msg)
            
            # Create an enhanced system message with KB context
            enhanced_system = SystemMessage(
                content=SYSTEM_PROMPT + f"\n\nRELEVANT KNOWLEDGE BASE CONTEXT:\n{kb_context[:1500]}"
            )
            enhanced_messages = [enhanced_system] + state["messages"]
            enhanced_state = {**state, "messages": enhanced_messages}
        else:
            enhanced_state = state
        
        response = chain.invoke(enhanced_state)
        return {"messages": [response]}
    
    return agent_node


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Determine whether to call tools or end"""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, route to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
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
        if user_messages:
            latest_user_msg = user_messages[-1].content
            kb_context = KnowledgeBase.get_context_for_question(latest_user_msg)
        
        # Create enhanced system message
        enhanced_system = SystemMessage(
            content=SYSTEM_PROMPT + (f"\n\nRELEVANT KNOWLEDGE BASE CONTEXT:\n{kb_context[:1500]}" if kb_context else "")
        )
        enhanced_messages = [enhanced_system] + state["messages"]
        
        # Use prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        # Update the last system message with KB context if available
        if kb_context:
            messages_with_context = [
                SystemMessage(content=SYSTEM_PROMPT + f"\n\nRELEVANT KNOWLEDGE BASE CONTEXT:\n{kb_context[:1500]}"),
                *[msg for msg in state["messages"] if not isinstance(msg, SystemMessage)]
            ]
        else:
            messages_with_context = enhanced_messages
        
        response = llm_with_tools.invoke(messages_with_context)
        
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

