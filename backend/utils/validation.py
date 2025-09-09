"""
Validation utilities for AI Expense Auditor
"""

import re
from datetime import datetime, date
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

class ValidationUtils:
    """Validation utilities for invoice data"""
    
    def __init__(self):
        # Validation patterns
        self.patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^\+?[\d\s\-\(\)]{10,}$',
            'currency': r'^[A-Z]{3}$',
            'invoice_number': r'^[A-Z0-9\-_]+$',
            'amount': r'^\d+(\.\d{1,2})?$'
        }
        
        # Required fields for invoice validation
        self.required_invoice_fields = [
            'vendor_name', 'amount', 'invoice_date'
        ]
        
        # Required fields for user validation
        self.required_user_fields = [
            'username', 'email', 'password'
        ]
    
    def validate_file(self, file_path: str) -> bool:
        """Validate uploaded file"""
        try:
            import os
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.warning("File does not exist", file_path=file_path)
                return False
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.warning("File is empty", file_path=file_path)
                return False
            
            # Check file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.json']
            if file_ext not in allowed_extensions:
                logger.warning("Invalid file extension", 
                              file_path=file_path, 
                              extension=file_ext)
                return False
            
            return True
            
        except Exception as e:
            logger.error("File validation failed", 
                        file_path=file_path, 
                        error=str(e))
            return False
    
    def validate_invoice_data(self, invoice_data: Dict[str, Any]) -> bool:
        """Validate extracted invoice data"""
        try:
            if not isinstance(invoice_data, dict):
                logger.warning("Invoice data is not a dictionary")
                return False
            
            # Check required fields
            missing_fields = []
            for field in self.required_invoice_fields:
                if not invoice_data.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning("Missing required fields", 
                              missing_fields=missing_fields)
                return False
            
            # Validate individual fields
            validation_results = {
                'vendor_name': self._validate_vendor_name(invoice_data.get('vendor_name')),
                'amount': self._validate_amount(invoice_data.get('amount')),
                'invoice_date': self._validate_date(invoice_data.get('invoice_date')),
                'currency': self._validate_currency(invoice_data.get('currency')),
                'invoice_number': self._validate_invoice_number(invoice_data.get('invoice_number'))
            }
            
            # Check if any critical validations failed
            critical_fields = ['vendor_name', 'amount', 'invoice_date']
            for field in critical_fields:
                if not validation_results.get(field, True):
                    logger.warning("Critical field validation failed", 
                                  field=field)
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Invoice data validation failed", error=str(e))
            return False
    
    def validate_user_data(self, user_data: Dict[str, Any]) -> bool:
        """Validate user data"""
        try:
            if not isinstance(user_data, dict):
                return False
            
            # Check required fields
            missing_fields = []
            for field in self.required_user_fields:
                if not user_data.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning("Missing required user fields", 
                              missing_fields=missing_fields)
                return False
            
            # Validate individual fields
            if not self._validate_email(user_data.get('email')):
                logger.warning("Invalid email format", 
                              email=user_data.get('email'))
                return False
            
            if not self._validate_username(user_data.get('username')):
                logger.warning("Invalid username format", 
                              username=user_data.get('username'))
                return False
            
            if not self._validate_password(user_data.get('password')):
                logger.warning("Invalid password format")
                return False
            
            return True
            
        except Exception as e:
            logger.error("User data validation failed", error=str(e))
            return False
    
    def _validate_vendor_name(self, vendor_name: str) -> bool:
        """Validate vendor name"""
        if not vendor_name or not isinstance(vendor_name, str):
            return False
        
        # Check length
        if len(vendor_name.strip()) < 2 or len(vendor_name) > 200:
            return False
        
        # Check for valid characters
        if not re.match(r'^[A-Za-z0-9\s\.,&\-]+$', vendor_name):
            return False
        
        return True
    
    def _validate_amount(self, amount: Any) -> bool:
        """Validate amount"""
        if amount is None:
            return False
        
        try:
            # Convert to float
            amount_float = float(amount)
            
            # Check range
            if amount_float < 0 or amount_float > 1000000:
                return False
            
            # Check decimal places
            if isinstance(amount, str):
                if not re.match(self.patterns['amount'], amount):
                    return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def _validate_date(self, date_str: str) -> bool:
        """Validate date string"""
        if not date_str or not isinstance(date_str, str):
            return False
        
        try:
            # Try to parse the date
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            try:
                # Try other common formats
                datetime.strptime(date_str, '%m/%d/%Y')
                return True
            except ValueError:
                try:
                    datetime.strptime(date_str, '%d/%m/%Y')
                    return True
                except ValueError:
                    return False
    
    def _validate_currency(self, currency: str) -> bool:
        """Validate currency code"""
        if not currency:
            return True  # Optional field
        
        if not isinstance(currency, str):
            return False
        
        return re.match(self.patterns['currency'], currency.upper()) is not None
    
    def _validate_invoice_number(self, invoice_number: str) -> bool:
        """Validate invoice number"""
        if not invoice_number:
            return True  # Optional field
        
        if not isinstance(invoice_number, str):
            return False
        
        # Check length
        if len(invoice_number) < 1 or len(invoice_number) > 100:
            return False
        
        return re.match(self.patterns['invoice_number'], invoice_number) is not None
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address"""
        if not email or not isinstance(email, str):
            return False
        
        return re.match(self.patterns['email'], email) is not None
    
    def _validate_username(self, username: str) -> bool:
        """Validate username"""
        if not username or not isinstance(username, str):
            return False
        
        # Check length
        if len(username) < 3 or len(username) > 50:
            return False
        
        # Check characters (alphanumeric and underscore only)
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False
        
        return True
    
    def _validate_password(self, password: str) -> bool:
        """Validate password"""
        if not password or not isinstance(password, str):
            return False
        
        # Check length
        if len(password) < 6 or len(password) > 128:
            return False
        
        # Check for at least one letter and one number
        if not re.search(r'[A-Za-z]', password):
            return False
        
        if not re.search(r'[0-9]', password):
            return False
        
        return True
    
    def sanitize_input(self, input_str: str) -> str:
        """Sanitize user input"""
        if not input_str or not isinstance(input_str, str):
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', input_str)
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        return sanitized
    
    def validate_fraud_analysis(self, fraud_analysis: Dict[str, Any]) -> bool:
        """Validate fraud analysis results"""
        try:
            if not isinstance(fraud_analysis, dict):
                return False
            
            # Check required fields
            required_fields = ['overall_score', 'flags', 'risk_level']
            for field in required_fields:
                if field not in fraud_analysis:
                    return False
            
            # Validate score range
            score = fraud_analysis.get('overall_score')
            if not isinstance(score, (int, float)) or not (0 <= score <= 1):
                return False
            
            # Validate flags
            flags = fraud_analysis.get('flags')
            if not isinstance(flags, list):
                return False
            
            # Validate risk level
            risk_level = fraud_analysis.get('risk_level')
            valid_risk_levels = ['low', 'medium', 'high', 'unknown']
            if risk_level not in valid_risk_levels:
                return False
            
            return True
            
        except Exception as e:
            logger.error("Fraud analysis validation failed", error=str(e))
            return False
