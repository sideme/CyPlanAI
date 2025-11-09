from typing import List, Dict, Any
from models import db, AgentSession, AgentMessage, Plan, Framework
from services.plan_generator import generate_plan_summary
from services.knowledge_base import KnowledgeBase
from models import Threat
from config import Config

# LangChain chat models
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama


class AgentService:
    """Minimal agent loop: plan → choose tool → act → write to memory."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    def start_session(self, plan_id: str | None = None) -> AgentSession:
        session = AgentSession(userId=self.user_id, planId=plan_id)
        db.session.add(session)
        db.session.commit()
        self._remember(session.sessionId, 'assistant', 'Hello! I am CyPlanAI. Tell me your scope and goals.')
        return session

    def _remember(self, session_id: str, role: str, content: str) -> AgentMessage:
        msg = AgentMessage(sessionId=session_id, role=role, content=content)
        db.session.add(msg)
        db.session.commit()
        return msg

    def _get_llm(self):
        provider = (Config.LLM_PROVIDER or 'openai').lower()
        if provider == 'openai' and Config.OPENAI_API_KEY:
            return ChatOpenAI(api_key=Config.OPENAI_API_KEY, model=Config.OPENAI_MODEL, temperature=0.4)
        if provider == 'anthropic' and Config.ANTHROPIC_API_KEY:
            return ChatAnthropic(api_key=Config.ANTHROPIC_API_KEY, model=Config.ANTHROPIC_MODEL, temperature=0.4)
        if provider == 'ollama':
            return ChatOllama(base_url=Config.OLLAMA_BASE_URL, model=Config.OLLAMA_MODEL, temperature=0.4)
        return None

    def _chat_response(self, session_id: str, user_text: str) -> str:
        """Free-form chat via LangChain with short system prompt and memory context."""
        llm = self._get_llm()
        if not llm:
            # fallback simple text
            return 'LLM is not configured. Set LLM_PROVIDER in backend/.env.'

        # fetch last few messages from this session for lightweight memory
        recent_msgs = AgentMessage.query.filter_by(sessionId=session_id).order_by(AgentMessage.timestamp.asc()).all()
        chat_history = []
        for m in recent_msgs[-10:]:
            role = 'assistant' if m.role == 'assistant' else 'user'
            chat_history.append({ 'role': role, 'content': m.content })

        # Retrieve relevant knowledge from knowledge base (RAG)
        kb_context = KnowledgeBase.get_context_for_question(user_text)

        system_text = (
            "You are CyPlanAI, a cybersecurity planning agent. Use the provided knowledge base context "
            "to answer questions accurately. Always cite specific framework controls (e.g., 'ISO 27001 A.8.1.1' or "
            "'NIST CSF PR.AC-3') when mentioning them. Be concise and factual. If information is not in the "
            "knowledge base, say so rather than guessing.\n\n"
            "KNOWLEDGE BASE CONTEXT:\n" + kb_context[:2000]  # Limit context size
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_text),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{question}")
        ])
        chain = prompt | llm | StrOutputParser()
        rendered_history = [(m['role'], m['content']) for m in chat_history]
        return chain.invoke({ 'history': rendered_history, 'question': user_text })

    def _tool_framework_info(self, framework_id: str) -> Dict[str, Any]:
        fw = Framework.query.get(framework_id)
        return fw.to_dict() if fw else {}

    def _tool_risk_score(self, hints: List[str]) -> List[Dict[str, Any]]:
        # naive mapping to threats by keyword presence
        mapping = {
            'phish': 'Phishing leading to credential theft',
            'poison': 'Data poisoning (ML)'
        }
        seen = set()
        for h in hints:
            l = h.lower()
            for k, name in mapping.items():
                if k in l:
                    seen.add(name)
        results = []
        for name in seen:
            t = Threat.query.filter_by(name=name).first()
            if not t:
                continue
            results.append({'threat': t.to_dict(), 'score': (t.likelihood or 2) * (t.impact or 3)})
        return results

    def user_message(self, session_id: str, content: str) -> Dict[str, Any]:
        self._remember(session_id, 'user', content)

        # very simple planner: detect intents
        intent = 'chat'
        if 'generate' in content.lower() and 'summary' in content.lower():
            intent = 'generate_summary'
        elif 'framework' in content.lower():
            intent = 'framework_info'
        elif 'risk' in content.lower() or 'score' in content.lower():
            intent = 'risk_score'

        result: Dict[str, Any] = {'intent': intent}

        if intent == 'generate_summary':
            session = AgentSession.query.get(session_id)
            plan = Plan.query.get(session.planId) if session and session.planId else None
            if not plan:
                reply = 'No active plan is attached to this session. Create/attach a plan first.'
            else:
                summary = generate_plan_summary(plan, plan.framework.prompts if plan.framework else [], plan.responses)
                plan.summary = summary
                db.session.commit()
                reply = 'Generated the plan summary and saved it to your plan.'
            self._remember(session_id, 'assistant', reply)
            result['message'] = reply
        elif intent == 'framework_info':
            # try to find a framework id in the text, default to the plan's framework
            session = AgentSession.query.get(session_id)
            framework_id = None
            if session and session.planId:
                plan = Plan.query.get(session.planId)
                framework_id = plan.frameworkId if plan else None
            info = self._tool_framework_info(framework_id) if framework_id else {}
            reply = f"Framework info: {info.get('name','N/A')} — {info.get('description','No description')}"
            self._remember(session_id, 'assistant', reply)
            result['message'] = reply
        elif intent == 'risk_score':
            scores = self._tool_risk_score([content])
            if scores:
                lines = [f"- {r['threat']['name']}: score {r['score']}" for r in scores]
                reply = "Risk scoring results:\n" + "\n".join(lines)
            else:
                reply = 'No known threats detected from your input. Mention risks like phishing or data poisoning.'
            self._remember(session_id, 'assistant', reply)
            result['message'] = reply
        else:
            # Free chat via LLM (LangChain)
            reply = self._chat_response(session_id, content)
            self._remember(session_id, 'assistant', reply)
            result['message'] = reply

        return result


