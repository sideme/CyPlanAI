from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from models import Prompt

prompts_bp = Blueprint('prompts', __name__)

@prompts_bp.route('/framework/<framework_id>', methods=['GET'])
@jwt_required()
def get_prompts_by_framework(framework_id):
    """Get all prompts for a specific framework"""
    prompts = Prompt.query.filter_by(frameworkId=framework_id).order_by(Prompt.order).all()
    return jsonify([p.to_dict() for p in prompts]), 200

@prompts_bp.route('/<prompt_id>', methods=['GET'])
@jwt_required()
def get_prompt(prompt_id):
    """Get specific prompt details"""
    prompt = Prompt.query.get(prompt_id)
    
    if not prompt:
        return jsonify({'error': 'Prompt not found'}), 404
    
    return jsonify(prompt.to_dict()), 200

