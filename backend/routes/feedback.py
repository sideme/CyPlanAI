from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Feedback
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('', methods=['POST'])
@jwt_required()
def submit_feedback():
    """Submit user feedback (max 500 characters)"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('message'):
        return jsonify({'error': 'Feedback message is required'}), 400
    
    message = data['message'].strip()
    
    # Validate character limit (500 as per requirements)
    if len(message) > 500:
        return jsonify({'error': 'Feedback message must not exceed 500 characters'}), 400
    
    if len(message) == 0:
        return jsonify({'error': 'Feedback message cannot be empty'}), 400
    
    # Create feedback
    feedback = Feedback(
        userId=user_id,
        planId=data.get('planId'),
        message=message,
        timestamp=datetime.utcnow()
    )
    
    db.session.add(feedback)
    db.session.commit()
    
    return jsonify({
        'message': 'Feedback submitted successfully',
        'feedback': feedback.to_dict()
    }), 201

@feedback_bp.route('', methods=['GET'])
@jwt_required()
def get_feedback():
    """Get feedback (admin/instructor only - for future use)"""
    user_id = get_jwt_identity()
    from models import User
    user = User.query.get(user_id)
    
    # Only allow admin/instructor to view all feedback
    if user.role not in ['admin', 'instructor']:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    feedback_list = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    return jsonify([f.to_dict() for f in feedback_list]), 200

