"""
Audit Log model for AI Expense Auditor
"""

import json
from datetime import datetime
from .base import db

class AuditLog(db.Model):
    """Audit log model for tracking all system activities"""
    
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)  # invoice, user, system
    resource_id = db.Column(db.String(100), nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON details
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by user {self.user_id}>'
    
    def get_details(self):
        """Get details as dictionary"""
        if self.details:
            try:
                return json.loads(self.details)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_details(self, details):
        """Set details from dictionary"""
        self.details = json.dumps(details) if details else None
    
    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'invoice_id': self.invoice_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.get_details(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @staticmethod
    def log_action(user_id, action, resource_type=None, resource_id=None, details=None, 
                   ip_address=None, user_agent=None):
        """Create a new audit log entry"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        audit_log.set_details(details)
        
        db.session.add(audit_log)
        db.session.commit()
        
        return audit_log
    
    @staticmethod
    def get_by_user(user_id, limit=100):
        """Get audit logs for a specific user"""
        return AuditLog.query.filter_by(user_id=user_id)\
                            .order_by(AuditLog.timestamp.desc())\
                            .limit(limit).all()
    
    @staticmethod
    def get_by_invoice(invoice_id):
        """Get audit logs for a specific invoice"""
        return AuditLog.query.filter_by(invoice_id=invoice_id)\
                            .order_by(AuditLog.timestamp.desc()).all()
    
    @staticmethod
    def get_by_action(action, limit=100):
        """Get audit logs for a specific action"""
        return AuditLog.query.filter_by(action=action)\
                            .order_by(AuditLog.timestamp.desc())\
                            .limit(limit).all()
    
    @staticmethod
    def get_recent(limit=100):
        """Get recent audit logs"""
        return AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

