"""
Authentication utilities for AI Expense Auditor
"""

from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User
import structlog

logger = structlog.get_logger()

def require_permission(permission: str):
    """
    Decorator to require specific permission
    
    Args:
        permission: Required permission (read, write, delete, admin, audit, approve)
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
                user_id = get_jwt_identity()
                user = User.query.get(user_id)
                
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                
                if not user.is_active:
                    return jsonify({'error': 'Account is disabled'}), 403
                
                if not user.has_permission(permission):
                    logger.warning("Permission denied", 
                                  user_id=user_id, 
                                  permission=permission,
                                  user_role=user.role)
                    return jsonify({'error': 'Insufficient permissions'}), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error("Permission check failed", error=str(e))
                return jsonify({'error': 'Permission check failed'}), 500
        
        return decorated_function
    return decorator

def require_role(role: str):
    """
    Decorator to require specific role
    
    Args:
        role: Required role (admin, auditor, manager, user)
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
                user_id = get_jwt_identity()
                user = User.query.get(user_id)
                
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                
                if not user.is_active:
                    return jsonify({'error': 'Account is disabled'}), 403
                
                if user.role != role:
                    logger.warning("Role access denied", 
                                  user_id=user_id, 
                                  required_role=role,
                                  user_role=user.role)
                    return jsonify({'error': 'Insufficient role privileges'}), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error("Role check failed", error=str(e))
                return jsonify({'error': 'Role check failed'}), 500
        
        return decorated_function
    return decorator

def get_current_user():
    """Get current authenticated user"""
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return None
        
        user = User.query.get(user_id)
        return user if user and user.is_active else None
        
    except Exception as e:
        logger.error("Get current user failed", error=str(e))
        return None

def log_user_action(action: str, resource_type: str = None, resource_id: str = None, details: dict = None):
    """
    Log user action for audit trail
    
    Args:
        action: Action performed
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        details: Additional details
    """
    try:
        from models import AuditLog
        
        user_id = get_jwt_identity()
        if not user_id:
            return
        
        AuditLog.log_action(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
    except Exception as e:
        logger.error("Log user action failed", error=str(e))

def validate_jwt_token():
    """Validate JWT token and return user info"""
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return None
        
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return None
        
        return user.to_dict()
        
    except Exception as e:
        logger.error("JWT token validation failed", error=str(e))
        return None
