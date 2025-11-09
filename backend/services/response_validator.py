"""
Response Validator Service - Validates user responses
"""

def validate_response(value):
    """
    Validate a user response
    Returns: {'valid': bool, 'message': str}
    """
    if not value or not isinstance(value, str):
        return {'valid': False, 'message': 'Response value is required'}
    
    value = value.strip()
    
    if len(value) == 0:
        return {'valid': False, 'message': 'Response cannot be empty'}
    
    if len(value) > 10000:  # Reasonable limit
        return {'valid': False, 'message': 'Response is too long (max 10000 characters)'}
    
    return {'valid': True, 'message': 'Response validated successfully'}

