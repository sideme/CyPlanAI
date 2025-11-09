from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db, Framework, Control
from flask import current_app

frameworks_bp = Blueprint('frameworks', __name__)

@frameworks_bp.route('', methods=['GET'])
@jwt_required()
def get_frameworks():
    """Get all available cybersecurity frameworks"""
    frameworks = Framework.query.order_by(Framework.name).all()
    return jsonify([f.to_dict() for f in frameworks]), 200

@frameworks_bp.route('/<framework_id>', methods=['GET'])
@jwt_required()
def get_framework(framework_id):
    """Get specific framework details"""
    framework = Framework.query.get(framework_id)
    
    if not framework:
        return jsonify({'error': 'Framework not found'}), 404
    
    return jsonify(framework.to_dict()), 200

@frameworks_bp.route('/<framework_id>/info', methods=['GET'])
@jwt_required()
def get_framework_info(framework_id):
    """Get detailed framework information including controls and guidance"""
    framework = Framework.query.get(framework_id)
    
    if not framework:
        return jsonify({'error': 'Framework not found'}), 404
    
    # Enhanced framework info with prompts count
    info = framework.to_dict()
    info['prompts_count'] = len(framework.prompts)
    info['prompts'] = [p.to_dict() for p in sorted(framework.prompts, key=lambda x: x.order)]
    info['llm_provider'] = current_app.config.get('LLM_PROVIDER', 'openai')
    info['llm_model'] = current_app.config.get('OPENAI_MODEL') or current_app.config.get('ANTHROPIC_MODEL') or current_app.config.get('OLLAMA_MODEL')
    
    return jsonify(info), 200

@frameworks_bp.route('/<framework_id>/controls', methods=['GET'])
@jwt_required()
def get_framework_controls(framework_id):
    """List normalized controls for a framework."""
    ctrls = Control.query.filter_by(frameworkId=framework_id).all()
    return jsonify([c.to_dict() for c in ctrls]), 200

