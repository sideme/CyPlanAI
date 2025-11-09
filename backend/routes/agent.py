from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.agent_service import AgentService
from models import AgentSession

agent_bp = Blueprint('agent', __name__)


@agent_bp.route('/session', methods=['POST'])
@jwt_required()
def start_session():
    user_id = get_jwt_identity()
    plan_id = (request.get_json() or {}).get('planId')
    service = AgentService(user_id)
    session = service.start_session(plan_id)
    return jsonify({'session': session.to_dict(), 'llm': {
        'provider': current_app.config.get('LLM_PROVIDER', 'openai'),
        'model': current_app.config.get('OPENAI_MODEL') or current_app.config.get('ANTHROPIC_MODEL') or current_app.config.get('OLLAMA_MODEL')
    }}), 201


@agent_bp.route('/session/<session_id>/message', methods=['POST'])
@jwt_required()
def session_message(session_id):
    user_id = get_jwt_identity()
    content = (request.get_json() or {}).get('content', '')
    service = AgentService(user_id)
    result = service.user_message(session_id, content)
    return jsonify(result), 200


