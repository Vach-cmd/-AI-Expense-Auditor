"""
Invoice model for AI Expense Auditor
"""

import json
from datetime import datetime
from .base import db

class Invoice(db.Model):
    """Invoice model for storing processed invoices"""
    
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(100), nullable=True, index=True)
    vendor_name = db.Column(db.String(200), nullable=True, index=True)
    vendor_address = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=True)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=True)
    total_amount = db.Column(db.Numeric(10, 2), nullable=True)
    invoice_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True, index=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(10), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    
    # Extracted data (JSON)
    extracted_data = db.Column(db.Text, nullable=True)
    
    # Fraud detection results
    fraud_score = db.Column(db.Float, default=0.0, nullable=False, index=True)
    fraud_flags = db.Column(db.Text, nullable=True)  # JSON array of flags
    fraud_analysis = db.Column(db.Text, nullable=True)  # Full analysis JSON
    
    # Processing status
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)  # pending, processing, processed, failed
    processing_time = db.Column(db.Float, nullable=True)  # Processing time in seconds
    
    # Approval workflow
    approval_status = db.Column(db.String(20), default='pending', nullable=False, index=True)  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Audit fields
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    audit_logs = db.relationship('AuditLog', backref='invoice', lazy=True)
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number or self.id}>'
    
    def get_extracted_data(self):
        """Get extracted data as dictionary"""
        if self.extracted_data:
            try:
                return json.loads(self.extracted_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_extracted_data(self, data):
        """Set extracted data from dictionary"""
        self.extracted_data = json.dumps(data) if data else None
    
    def get_fraud_flags(self):
        """Get fraud flags as list"""
        if self.fraud_flags:
            try:
                return json.loads(self.fraud_flags)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_fraud_flags(self, flags):
        """Set fraud flags from list"""
        self.fraud_flags = json.dumps(flags) if flags else None
    
    def get_fraud_analysis(self):
        """Get fraud analysis as dictionary"""
        if self.fraud_analysis:
            try:
                return json.loads(self.fraud_analysis)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_fraud_analysis(self, analysis):
        """Set fraud analysis from dictionary"""
        self.fraud_analysis = json.dumps(analysis) if analysis else None
    
    def to_dict(self):
        """Convert invoice to dictionary"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'vendor_name': self.vendor_name,
            'vendor_address': self.vendor_address,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'tax_amount': float(self.tax_amount) if self.tax_amount else None,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'description': self.description,
            'category': self.category,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'extracted_data': self.get_extracted_data(),
            'fraud_score': self.fraud_score,
            'fraud_flags': self.get_fraud_flags(),
            'fraud_analysis': self.get_fraud_analysis(),
            'status': self.status,
            'processing_time': self.processing_time,
            'approval_status': self.approval_status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'processed_by': self.processed_by,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_by_status(status):
        """Get invoices by status"""
        return Invoice.query.filter_by(status=status).all()
    
    @staticmethod
    def get_by_fraud_score(min_score=0.5):
        """Get invoices with fraud score above threshold"""
        return Invoice.query.filter(Invoice.fraud_score >= min_score).all()
    
    @staticmethod
    def get_by_vendor(vendor_name):
        """Get invoices by vendor name"""
        return Invoice.query.filter_by(vendor_name=vendor_name).all()
    
    @staticmethod
    def get_by_user(user_id):
        """Get invoices processed by specific user"""
        return Invoice.query.filter_by(processed_by=user_id).all()

