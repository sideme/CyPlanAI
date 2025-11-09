"""
Plan Generator Service - LangChain-based, pluggable LLM providers
Providers: OpenAI, Anthropic, Ollama (local)
"""
import requests
from config import Config
from models import ControlMapping, Threat, Control

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama

def _build_citations_section(plan):
    """Build a structured citations section using ontology mappings if threats are inferred from responses."""
    # naive inference: look for keywords to map to threats
    keywords = {
        'phishing': 'Phishing leading to credential theft',
        'poison': 'Data poisoning (ML)',
        'poisoning': 'Data poisoning (ML)',
    }
    selected_threats = set()
    for r in plan.responses:
        text = (r.value or '').lower()
        for k, threat_name in keywords.items():
            if k in text:
                selected_threats.add(threat_name)

    if not selected_threats:
        return []

    threat_rows = []
    for name in selected_threats:
        t = Threat.query.filter_by(name=name).first()
        if not t:
            continue
        mappings = ControlMapping.query.filter_by(threatId=t.threatId).all()
        for m in mappings:
            c: Control = m.control
            threat_rows.append({
                'threat': t.to_dict(),
                'control': c.to_dict() if c else None,
                'evidence_hint': m.evidence_hint,
            })
    return threat_rows


def generate_plan_summary(plan, prompts, responses):
    """
    Generate a comprehensive cybersecurity plan summary using OpenAI
    Based on user responses and the selected framework
    """
    if not client:
        # Fallback if OpenAI API key not configured
        return generate_fallback_summary(plan, prompts, responses)
    
    # Build context from responses
    response_dict = {r.promptId: r.value for r in responses}
    
    # Organize responses by prompt
    responses_text = ""
    for i, prompt in enumerate(prompts, 1):
        response_value = response_dict.get(prompt.promptId, "Not answered")
        responses_text += f"\n\nPrompt {i} ({prompt.category}):\n"
        responses_text += f"Question: {prompt.text}\n"
        responses_text += f"Response: {response_value}\n"
    
    framework = plan.framework
    framework_name = framework.name if framework else "Selected Framework"
    framework_type = framework.type if framework else ""
    
    # Build the AI prompt
    system_prompt = """You are an expert cybersecurity consultant specializing in comprehensive cybersecurity planning. 
Your task is to generate a detailed, well-structured cybersecurity plan based on user responses to framework-specific prompts.
The plan should be professional, comprehensive, and include specific framework citations where applicable.
Format the plan with clear sections: Executive Summary, Scope, Risk Assessment, Controls Implementation, Monitoring, and Incident Response."""

    user_prompt = f"""Generate a comprehensive cybersecurity plan based on the following information:

Framework: {framework_name} ({framework_type})
User Responses to Planning Prompts:
{responses_text}

Please create a detailed cybersecurity plan that:
1. Summarizes the key findings from the user's responses
2. Identifies risks and vulnerabilities mentioned
3. Recommends specific controls aligned with the {framework_name} framework
4. Includes framework citations (e.g., "Control A.8.1.1 from ISO 27001" or "NIST CSF Identify Function")
5. Provides actionable implementation guidance
6. Outlines monitoring and incident response procedures
7. Follows professional cybersecurity planning standards

Structure the plan with clear sections and subsections."""

    try:
        provider = (Config.LLM_PROVIDER or 'openai').lower()

        # Build a LangChain prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system}"),
            ("user", "{user}")
        ])

        # Select model
        if provider == 'openai' and Config.OPENAI_API_KEY:
            llm = ChatOpenAI(
                api_key=Config.OPENAI_API_KEY,
                model=Config.OPENAI_MODEL,
                temperature=0.7,
                max_tokens=3000,
            )
        elif provider == 'anthropic' and Config.ANTHROPIC_API_KEY:
            llm = ChatAnthropic(
                api_key=Config.ANTHROPIC_API_KEY,
                model=Config.ANTHROPIC_MODEL,
                temperature=0.7,
                max_tokens=3000,
            )
        elif provider == 'ollama':
            llm = ChatOllama(
                base_url=Config.OLLAMA_BASE_URL,
                model=Config.OLLAMA_MODEL,
                temperature=0.7,
            )
        else:
            return generate_fallback_summary(plan, prompts, responses)

        chain = prompt | llm | StrOutputParser()
        generated_summary = chain.invoke({"system": system_prompt, "user": user_prompt})
        
        # Add framework metadata and citations
        citations = _build_citations_section(plan)
        citations_text = ""
        if citations:
            citations_text += "\n=== Framework Citations (Ontology-Driven) ===\n"
            for idx, row in enumerate(citations, 1):
                ctrl = row.get('control') or {}
                threat = row.get('threat') or {}
                citations_text += f"{idx}. Threat: {threat.get('name')} → Control: {ctrl.get('reference')} - {ctrl.get('title')}\n"
                if row.get('evidence_hint'):
                    citations_text += f"   Evidence: {row['evidence_hint']}\n"

        summary_with_metadata = f"""=== Cybersecurity Plan Summary ===
Framework: {framework_name}
Generated: {plan.created_at.strftime('%Y-%m-%d %H:%M:%S')}

{generated_summary}

{citations_text}
---
This plan was generated using CyPlanAI based on {framework_name} framework."""

        return summary_with_metadata
    
    except Exception as e:
        print(f"Error generating plan with OpenAI: {e}")
        return generate_fallback_summary(plan, prompts, responses)

def generate_fallback_summary(plan, prompts, responses):
    """Generate a basic summary without AI when OpenAI is unavailable"""
    framework = plan.framework
    framework_name = framework.name if framework else "Selected Framework"
    
    response_dict = {r.promptId: r.value for r in responses}
    
    summary = f"""=== Cybersecurity Plan Summary ===
Framework: {framework_name}
Generated: {plan.created_at.strftime('%Y-%m-%d %H:%M:%S')}

=== Executive Summary ===
This cybersecurity plan has been developed based on the {framework_name} framework. 
The plan incorporates responses to {len(prompts)} planning prompts covering key cybersecurity domains.

=== Scope ===
The plan addresses cybersecurity planning for the organization based on the selected framework requirements.

=== Key Responses Summary ===
"""
    
    for i, prompt in enumerate(prompts, 1):
        response_value = response_dict.get(prompt.promptId, "Not answered")
        summary += f"\n{i}. {prompt.category}: {response_value[:200]}...\n"
    
    summary += f"""

=== Controls Implementation ===
Based on the {framework_name} framework, controls should be implemented according to the responses provided.

=== Monitoring ===
Regular monitoring and review of the implemented controls is recommended.

=== Incident Response ===
An incident response plan should be developed and tested regularly.

---
This plan was generated using CyPlanAI based on {framework_name} framework.
Note: For enhanced plan generation, configure OpenAI API key in environment variables.
"""
    
    return summary

