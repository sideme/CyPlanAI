from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Response, Plan, Prompt
from datetime import datetime
from services.response_validator import validate_response

responses_bp = Blueprint('responses', __name__)

@responses_bp.route('', methods=['POST'])
@jwt_required()
def submit_response():
    """Submit a response to a prompt"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('planId') or not data.get('promptId') or not data.get('value'):
        return jsonify({'error': 'Missing required fields: planId, promptId, value'}), 400
    
    # Validate plan exists and belongs to user
    plan = Plan.query.get(data['planId'])
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    if plan.userId != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Validate prompt exists and belongs to the plan's framework
    prompt = Prompt.query.get(data['promptId'])
    if not prompt:
        return jsonify({'error': 'Prompt not found'}), 404
    
    if prompt.frameworkId != plan.frameworkId:
        return jsonify({'error': 'Prompt does not belong to this plan\'s framework'}), 400
    
    # Validate response value
    validation_result = validate_response(data['value'])
    if not validation_result['valid']:
        return jsonify({'error': validation_result['message']}), 400
    
    # Check if response already exists for this prompt in this plan
    existing_response = Response.query.filter_by(
        planId=data['planId'],
        promptId=data['promptId']
    ).first()
    
    if existing_response:
        # Update existing response
        existing_response.value = data['value']
        existing_response.timestamp = datetime.utcnow()
        db.session.commit()
        return jsonify(existing_response.to_dict()), 200
    
    # Create new response
    response = Response(
        planId=data['planId'],
        promptId=data['promptId'],
        value=data['value'],
        timestamp=datetime.utcnow()
    )
    
    db.session.add(response)
    db.session.commit()
    
    return jsonify(response.to_dict()), 201

@responses_bp.route('/plan/<plan_id>', methods=['GET'])
@jwt_required()
def get_responses_by_plan(plan_id):
    """Get all responses for a specific plan"""
    user_id = get_jwt_identity()
    plan = Plan.query.get(plan_id)
    
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    if plan.userId != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    responses = Response.query.filter_by(planId=plan_id).all()
    return jsonify([r.to_dict() for r in responses]), 200

