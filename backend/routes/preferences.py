from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, UserPreferences

preferences_bp = Blueprint('preferences', __name__)


@preferences_bp.route('/', methods=['GET'])
@jwt_required()
def get_preferences():
    """Get current user's preferences"""
    user_id = get_jwt_identity()
    prefs = UserPreferences.get_or_create(user_id)
    return jsonify(prefs.to_dict()), 200


@preferences_bp.route('/', methods=['PUT'])
@jwt_required()
def update_preferences():
    """Update current user's preferences"""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    prefs = UserPreferences.get_or_create(user_id)

    # Update only provided fields
    if 'theme' in data:
        if data['theme'] in ('light', 'dark'):
            prefs.theme = data['theme']
        else:
            return jsonify({'error': 'Invalid theme value. Must be "light" or "dark"'}), 400

    if 'hideToolCalls' in data:
        prefs.hideToolCalls = bool(data['hideToolCalls'])

    if 'apiUrl' in data:
        prefs.apiUrl = data['apiUrl'] if data['apiUrl'] else None

    if 'assistantId' in data:
        prefs.assistantId = data['assistantId'] if data['assistantId'] else None

    if 'sidebarOpen' in data:
        prefs.sidebarOpen = bool(data['sidebarOpen'])

    db.session.commit()

    return jsonify({
        'message': 'Preferences updated successfully',
        'preferences': prefs.to_dict()
    }), 200


@preferences_bp.route('/reset', methods=['POST'])
@jwt_required()
def reset_preferences():
    """Reset preferences to defaults"""
    user_id = get_jwt_identity()
    prefs = UserPreferences.query.filter_by(userId=user_id).first()

    if prefs:
        prefs.theme = 'dark'
        prefs.hideToolCalls = False
        prefs.apiUrl = None
        prefs.assistantId = None
        prefs.sidebarOpen = True
        db.session.commit()
    else:
        prefs = UserPreferences.get_or_create(user_id)

    return jsonify({
        'message': 'Preferences reset to defaults',
        'preferences': prefs.to_dict()
    }), 200

