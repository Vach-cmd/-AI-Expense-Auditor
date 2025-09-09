"""
Main invoice processing logic
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import structlog

from services.ocr_engine import OCREngine
from services.nlp_extractor import NLPExtractor
from services.fraud_detector import FraudDetector
from models import Invoice, AuditLog, db
from utils.file_handler import FileHandler
from utils.validation import ValidationUtils

logger = structlog.get_logger()

class InvoiceProcessor:
    """Main invoice processing class"""
    
    def __init__(self):
        self.ocr_engine = OCREngine()
        self.nlp_extractor = NLPExtractor()
        self.fraud_detector = FraudDetector()
        self.file_handler = FileHandler()
        self.validator = ValidationUtils()
    
    def process_invoice(self, file_path: str, user_id: int) -> Dict[str, Any]:
        """
        Process an invoice file and extract data
        
        Args:
            file_path: Path to the invoice file
            user_id: ID of the user processing the invoice
            
        Returns:
            Dictionary containing extracted data and fraud analysis
        """
        try:
            logger.info("Starting invoice processing", file_path=file_path, user_id=user_id)
            
            # Validate file
            if not self.validator.validate_file(file_path):
                raise ValueError("Invalid file format or corrupted file")
            
            # Extract text using OCR
            extracted_text = self.ocr_engine.extract_text(file_path)
            if not extracted_text:
                raise ValueError("No text could be extracted from the file")
            
            # Extract structured data using NLP
            extracted_data = self.nlp_extractor.extract_invoice_data(extracted_text)
            
            # Validate extracted data
            if not self.validator.validate_invoice_data(extracted_data):
                raise ValueError("Invalid invoice data extracted")
            
            # Perform fraud detection
            fraud_analysis = self.fraud_detector.analyze_invoice(extracted_data)
            
            # Create invoice record
            invoice = self._create_invoice_record(extracted_data, fraud_analysis, user_id, file_path)
            
            # Log audit trail
            self._log_audit_trail(invoice.id, user_id, "invoice_processed", {
                "file_path": file_path,
                "fraud_score": fraud_analysis.get('overall_score', 0),
                "fraud_flags": fraud_analysis.get('flags', [])
            })
            
            result = {
                "invoice_id": invoice.id,
                "extracted_data": extracted_data,
                "fraud_analysis": fraud_analysis,
                "status": "processed",
                "processing_time": datetime.now().isoformat()
            }
            
            logger.info("Invoice processing completed", 
                       invoice_id=invoice.id, 
                       fraud_score=fraud_analysis.get('overall_score', 0))
            
            return result
            
        except Exception as e:
            logger.error("Invoice processing failed", 
                        file_path=file_path, 
                        error=str(e))
            raise
    
    def batch_process_invoices(self, file_paths: List[str], user_id: int) -> List[Dict[str, Any]]:
        """
        Process multiple invoices in batch
        
        Args:
            file_paths: List of file paths to process
            user_id: ID of the user processing the invoices
            
        Returns:
            List of processing results
        """
        results = []
        
        for file_path in file_paths:
            try:
                result = self.process_invoice(file_path, user_id)
                results.append(result)
            except Exception as e:
                logger.error("Batch processing failed for file", 
                           file_path=file_path, 
                           error=str(e))
                results.append({
                    "file_path": file_path,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def reprocess_invoice(self, invoice_id: int, user_id: int) -> Dict[str, Any]:
        """
        Reprocess an existing invoice with updated fraud detection
        
        Args:
            invoice_id: ID of the invoice to reprocess
            user_id: ID of the user reprocessing the invoice
            
        Returns:
            Updated processing results
        """
        try:
            invoice = Invoice.query.get(invoice_id)
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")
            
            # Get original file path
            file_path = invoice.file_path
            if not os.path.exists(file_path):
                raise ValueError("Original file not found")
            
            # Reprocess with updated fraud detection
            result = self.process_invoice(file_path, user_id)
            
            # Update existing invoice record
            self._update_invoice_record(invoice, result['extracted_data'], result['fraud_analysis'])
            
            # Log audit trail
            self._log_audit_trail(invoice_id, user_id, "invoice_reprocessed", {
                "fraud_score": result['fraud_analysis'].get('overall_score', 0),
                "fraud_flags": result['fraud_analysis'].get('flags', [])
            })
            
            return result
            
        except Exception as e:
            logger.error("Invoice reprocessing failed", 
                        invoice_id=invoice_id, 
                        error=str(e))
            raise
    
    def _create_invoice_record(self, extracted_data: Dict[str, Any], 
                              fraud_analysis: Dict[str, Any], 
                              user_id: int, 
                              file_path: str) -> Invoice:
        """Create invoice database record"""
        invoice = Invoice(
            invoice_number=extracted_data.get('invoice_number'),
            vendor_name=extracted_data.get('vendor_name'),
            vendor_address=extracted_data.get('vendor_address'),
            amount=extracted_data.get('amount'),
            currency=extracted_data.get('currency', 'USD'),
            invoice_date=extracted_data.get('invoice_date'),
            due_date=extracted_data.get('due_date'),
            description=extracted_data.get('description'),
            category=extracted_data.get('category'),
            file_path=file_path,
            extracted_data=json.dumps(extracted_data),
            fraud_score=fraud_analysis.get('overall_score', 0),
            fraud_flags=json.dumps(fraud_analysis.get('flags', [])),
            fraud_analysis=json.dumps(fraud_analysis),
            status='processed',
            processed_by=user_id,
            processed_at=datetime.now()
        )
        
        from models import db
        db.session.add(invoice)
        db.session.commit()
        
        return invoice
    
    def _update_invoice_record(self, invoice: Invoice, 
                              extracted_data: Dict[str, Any], 
                              fraud_analysis: Dict[str, Any]):
        """Update existing invoice record"""
        invoice.extracted_data = json.dumps(extracted_data)
        invoice.fraud_score = fraud_analysis.get('overall_score', 0)
        invoice.fraud_flags = json.dumps(fraud_analysis.get('flags', []))
        invoice.fraud_analysis = json.dumps(fraud_analysis)
        invoice.status = 'reprocessed'
        invoice.processed_at = datetime.now()
        
        from models import db
        db.session.commit()
    
    def _log_audit_trail(self, invoice_id: int, user_id: int, 
                        action: str, details: Dict[str, Any]):
        """Log audit trail entry"""
        audit_log = AuditLog(
            invoice_id=invoice_id,
            user_id=user_id,
            action=action,
            details=json.dumps(details),
            timestamp=datetime.now()
        )
        
        from models import db
        db.session.add(audit_log)
        db.session.commit()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        from models import db
        
        total_invoices = Invoice.query.count()
        processed_invoices = Invoice.query.filter_by(status='processed').count()
        fraud_detected = Invoice.query.filter(Invoice.fraud_score > 0.5).count()
        
        return {
            "total_invoices": total_invoices,
            "processed_invoices": processed_invoices,
            "fraud_detected": fraud_detected,
            "processing_rate": processed_invoices / total_invoices if total_invoices > 0 else 0,
            "fraud_rate": fraud_detected / total_invoices if total_invoices > 0 else 0
        }
