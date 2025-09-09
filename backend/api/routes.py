"""
API routes for AI Expense Auditor
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from werkzeug.utils import secure_filename
import os
import structlog
from datetime import datetime, timedelta

from models import User, Invoice, AuditLog, db
from services.invoice_processor import InvoiceProcessor
from services.fraud_detector import FraudDetector
from utils.auth import require_permission
from utils.file_handler import FileHandler

logger = structlog.get_logger()

# Create blueprints
auth_bp = Blueprint('auth', __name__)
invoice_bp = Blueprint('invoices', __name__)
analytics_bp = Blueprint('analytics', __name__)
admin_bp = Blueprint('admin', __name__)

# Initialize services
invoice_processor = InvoiceProcessor()
fraud_detector = FraudDetector()
file_handler = FileHandler()

# Authentication routes
@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        user = User.get_by_username(username)
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is disabled'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES'])
        )
        
        # Log login
        AuditLog.log_action(
            user_id=user.id,
            action='user_login',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error("Login failed", error=str(e))
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/register', methods=['POST'])
@jwt_required()
@require_permission('admin')
def register():
    """User registration endpoint (admin only)"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')
        
        if not all([username, email, password]):
            return jsonify({'error': 'Username, email, and password required'}), 400
        
        # Check if user already exists
        if User.get_by_username(username):
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.get_by_email(email):
            return jsonify({'error': 'Email already exists'}), 400
        
        # Create new user
        user = User(
            username=username,
            email=email,
            role=role,
            first_name=data.get('first_name'),
            last_name=data.get('last_name')
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Log registration
        current_user_id = get_jwt_identity()
        AuditLog.log_action(
            user_id=current_user_id,
            action='user_created',
            resource_type='user',
            resource_id=str(user.id),
            details={'new_user': user.username, 'role': user.role}
        )
        
        return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201
        
    except Exception as e:
        logger.error("User registration failed", error=str(e))
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()})
        
    except Exception as e:
        logger.error("Get profile failed", error=str(e))
        return jsonify({'error': 'Failed to get profile'}), 500

# Invoice routes
@invoice_bp.route('/', methods=['POST'])
@jwt_required()
@require_permission('write')
def upload_invoice():
    """Upload and process invoice"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        if not file_handler.is_allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = file_handler.save_file(file, filename)
        
        # Process invoice
        user_id = get_jwt_identity()
        result = invoice_processor.process_invoice(file_path, user_id)
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error("Invoice upload failed", error=str(e))
        return jsonify({'error': 'Invoice processing failed'}), 500

@invoice_bp.route('/', methods=['GET'])
@jwt_required()
@require_permission('read')
def get_invoices():
    """Get invoices with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        fraud_score_min = request.args.get('fraud_score_min', type=float)
        vendor = request.args.get('vendor')
        
        query = Invoice.query
        
        # Apply filters
        if status:
            query = query.filter_by(status=status)
        if fraud_score_min is not None:
            query = query.filter(Invoice.fraud_score >= fraud_score_min)
        if vendor:
            query = query.filter(Invoice.vendor_name.ilike(f'%{vendor}%'))
        
        # Paginate results
        invoices = query.order_by(Invoice.created_at.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'invoices': [invoice.to_dict() for invoice in invoices.items],
            'total': invoices.total,
            'pages': invoices.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error("Get invoices failed", error=str(e))
        return jsonify({'error': 'Failed to get invoices'}), 500

@invoice_bp.route('/<int:invoice_id>', methods=['GET'])
@jwt_required()
@require_permission('read')
def get_invoice(invoice_id):
    """Get specific invoice"""
    try:
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        return jsonify({'invoice': invoice.to_dict()})
        
    except Exception as e:
        logger.error("Get invoice failed", error=str(e))
        return jsonify({'error': 'Failed to get invoice'}), 500

@invoice_bp.route('/<int:invoice_id>/approve', methods=['POST'])
@jwt_required()
@require_permission('approve')
def approve_invoice(invoice_id):
    """Approve invoice"""
    try:
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        invoice.approval_status = 'approved'
        invoice.approved_by = get_jwt_identity()
        invoice.approved_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log approval
        AuditLog.log_action(
            user_id=get_jwt_identity(),
            action='invoice_approved',
            resource_type='invoice',
            resource_id=str(invoice_id)
        )
        
        return jsonify({'message': 'Invoice approved successfully'})
        
    except Exception as e:
        logger.error("Invoice approval failed", error=str(e))
        return jsonify({'error': 'Failed to approve invoice'}), 500

@invoice_bp.route('/<int:invoice_id>/reject', methods=['POST'])
@jwt_required()
@require_permission('approve')
def reject_invoice(invoice_id):
    """Reject invoice"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        invoice.approval_status = 'rejected'
        invoice.approved_by = get_jwt_identity()
        invoice.approved_at = datetime.utcnow()
        invoice.rejection_reason = reason
        
        db.session.commit()
        
        # Log rejection
        AuditLog.log_action(
            user_id=get_jwt_identity(),
            action='invoice_rejected',
            resource_type='invoice',
            resource_id=str(invoice_id),
            details={'reason': reason}
        )
        
        return jsonify({'message': 'Invoice rejected successfully'})
        
    except Exception as e:
        logger.error("Invoice rejection failed", error=str(e))
        return jsonify({'error': 'Failed to reject invoice'}), 500

# Analytics routes
@analytics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@require_permission('read')
def get_dashboard_data():
    """Get dashboard analytics data"""
    try:
        # Get basic statistics
        total_invoices = Invoice.query.count()
        processed_invoices = Invoice.query.filter_by(status='processed').count()
        pending_invoices = Invoice.query.filter_by(status='pending').count()
        fraud_detected = Invoice.query.filter(Invoice.fraud_score > 0.5).count()
        
        # Get recent invoices
        recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(10).all()
        
        # Get fraud trends (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        fraud_trend = Invoice.query.filter(
            Invoice.created_at >= thirty_days_ago,
            Invoice.fraud_score > 0.5
        ).count()
        
        return jsonify({
            'statistics': {
                'total_invoices': total_invoices,
                'processed_invoices': processed_invoices,
                'pending_invoices': pending_invoices,
                'fraud_detected': fraud_detected,
                'processing_rate': processed_invoices / total_invoices if total_invoices > 0 else 0,
                'fraud_rate': fraud_detected / total_invoices if total_invoices > 0 else 0
            },
            'recent_invoices': [invoice.to_dict() for invoice in recent_invoices],
            'fraud_trend': fraud_trend
        })
        
    except Exception as e:
        logger.error("Get dashboard data failed", error=str(e))
        return jsonify({'error': 'Failed to get dashboard data'}), 500

@analytics_bp.route('/fraud-analysis', methods=['GET'])
@jwt_required()
@require_permission('audit')
def get_fraud_analysis():
    """Get detailed fraud analysis"""
    try:
        # Get fraud statistics by category
        fraud_by_category = db.session.query(
            Invoice.category,
            db.func.count(Invoice.id).label('count'),
            db.func.avg(Invoice.fraud_score).label('avg_score')
        ).filter(Invoice.fraud_score > 0.5)\
         .group_by(Invoice.category)\
         .all()
        
        # Get top fraudulent vendors
        top_fraudulent_vendors = db.session.query(
            Invoice.vendor_name,
            db.func.count(Invoice.id).label('count'),
            db.func.avg(Invoice.fraud_score).label('avg_score')
        ).filter(Invoice.fraud_score > 0.5)\
         .group_by(Invoice.vendor_name)\
         .order_by(db.func.count(Invoice.id).desc())\
         .limit(10)\
         .all()
        
        return jsonify({
            'fraud_by_category': [
                {
                    'category': item.category or 'Unknown',
                    'count': item.count,
                    'avg_score': float(item.avg_score)
                }
                for item in fraud_by_category
            ],
            'top_fraudulent_vendors': [
                {
                    'vendor_name': item.vendor_name or 'Unknown',
                    'count': item.count,
                    'avg_score': float(item.avg_score)
                }
                for item in top_fraudulent_vendors
            ]
        })
        
    except Exception as e:
        logger.error("Get fraud analysis failed", error=str(e))
        return jsonify({'error': 'Failed to get fraud analysis'}), 500

# Admin routes
@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@require_permission('admin')
def get_users():
    """Get all users (admin only)"""
    try:
        users = User.query.all()
        return jsonify({'users': [user.to_dict() for user in users]})
        
    except Exception as e:
        logger.error("Get users failed", error=str(e))
        return jsonify({'error': 'Failed to get users'}), 500

@admin_bp.route('/audit-logs', methods=['GET'])
@jwt_required()
@require_permission('admin')
def get_audit_logs():
    """Get audit logs (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        logs = AuditLog.query.order_by(AuditLog.timestamp.desc())\
                            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'logs': [log.to_dict() for log in logs.items],
            'total': logs.total,
            'pages': logs.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error("Get audit logs failed", error=str(e))
        return jsonify({'error': 'Failed to get audit logs'}), 500
