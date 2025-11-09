from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Plan, Framework, Response, Prompt
from datetime import datetime
from services.plan_generator import generate_plan_summary

plans_bp = Blueprint('plans', __name__)

@plans_bp.route('', methods=['GET'])
@jwt_required()
def get_plans():
    """Get all plans for the current user"""
    user_id = get_jwt_identity()
    plans = Plan.query.filter_by(userId=user_id).order_by(Plan.created_at.desc()).all()
    return jsonify([p.to_dict() for p in plans]), 200

@plans_bp.route('', methods=['POST'])
@jwt_required()
def create_plan():
    """Start a new planning session"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('frameworkId'):
        return jsonify({'error': 'Framework ID is required'}), 400
    
    framework = Framework.query.get(data['frameworkId'])
    if not framework:
        return jsonify({'error': 'Framework not found'}), 404
    
    # Create new plan
    plan = Plan(
        userId=user_id,
        frameworkId=data['frameworkId'],
        status='in_progress'
    )
    
    db.session.add(plan)
    db.session.commit()
    
    return jsonify(plan.to_dict()), 201

@plans_bp.route('/<plan_id>', methods=['GET'])
@jwt_required()
def get_plan(plan_id):
    """Get specific plan details"""
    user_id = get_jwt_identity()
    plan = Plan.query.get(plan_id)
    
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    # Check authorization
    if plan.userId != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    plan_dict = plan.to_dict()
    plan_dict['responses'] = [r.to_dict() for r in plan.responses]
    
    # Get prompts for this framework
    prompts = Prompt.query.filter_by(frameworkId=plan.frameworkId).order_by(Prompt.order).all()
    plan_dict['prompts'] = [p.to_dict() for p in prompts]
    
    return jsonify(plan_dict), 200

@plans_bp.route('/<plan_id>/resume', methods=['GET'])
@jwt_required()
def resume_plan(plan_id):
    """Resume a planning session - get next unanswered prompt"""
    user_id = get_jwt_identity()
    plan = Plan.query.get(plan_id)
    
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    if plan.userId != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Get all prompts for this framework
    prompts = Prompt.query.filter_by(frameworkId=plan.frameworkId).order_by(Prompt.order).all()
    
    # Get already answered prompt IDs
    answered_prompt_ids = {r.promptId for r in plan.responses}
    
    # Find next unanswered prompt
    next_prompt = None
    for prompt in prompts:
        if prompt.promptId not in answered_prompt_ids:
            next_prompt = prompt
            break
    
    if not next_prompt:
        # All prompts answered, return completion status
        return jsonify({
            'plan': plan.to_dict(),
            'next_prompt': None,
            'completed': True,
            'message': 'All prompts completed. Generate summary to complete the plan.'
        }), 200
    
    return jsonify({
        'plan': plan.to_dict(),
        'next_prompt': next_prompt.to_dict(),
        'completed': False
    }), 200

@plans_bp.route('/<plan_id>/generate-summary', methods=['POST'])
@jwt_required()
def generate_summary(plan_id):
    """Generate summary plan from all responses"""
    user_id = get_jwt_identity()
    plan = Plan.query.get(plan_id)
    
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    if plan.userId != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Get all prompts for this framework
    prompts = Prompt.query.filter_by(frameworkId=plan.frameworkId).order_by(Prompt.order).all()
    answered_prompt_ids = {r.promptId for r in plan.responses}
    
    # Validate all prompts are answered
    prompt_ids = {p.promptId for p in prompts}
    if prompt_ids != answered_prompt_ids:
        return jsonify({
            'error': 'All prompts must be answered before generating summary',
            'missing_prompts': len(prompt_ids - answered_prompt_ids)
        }), 400
    
    # Generate plan summary using AI
    responses = plan.responses
    summary = generate_plan_summary(plan, prompts, responses)
    
    plan.summary = summary
    plan.status = 'completed'
    plan.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'plan': plan.to_dict(),
        'summary': summary
    }), 200

@plans_bp.route('/<plan_id>/export', methods=['GET'])
@jwt_required()
def export_plan(plan_id):
    """Export plan as PDF or JSON"""
    from services.export_service import export_plan_to_pdf, export_plan_to_json
    
    user_id = get_jwt_identity()
    plan = Plan.query.get(plan_id)
    
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    if plan.userId != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    format_type = request.args.get('format', 'json').lower()
    
    if format_type == 'pdf':
        pdf_data = export_plan_to_pdf(plan)
        from flask import Response
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename=plan_{plan.planId}.pdf'}
        )
    else:
        json_data = export_plan_to_json(plan)
        return jsonify(json_data), 200

