"""
Fraud Detection Engine for Invoice Analysis
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import structlog

from models import Invoice, db

logger = structlog.get_logger()

class FraudDetector:
    """Fraud detection engine for analyzing invoices"""
    
    def __init__(self):
        # Fraud detection thresholds
        self.thresholds = {
            'duplicate': 0.8,
            'inflation': 1.5,
            'ghost_vendor': 0.7,
            'split_billing': 0.9,
            'suspicious_patterns': 0.6
        }
        
        # Initialize TF-IDF vectorizer for text similarity
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Suspicious patterns
        self.suspicious_patterns = {
            'round_amounts': r'^\d+\.00$',
            'sequential_invoices': r'INV-\d{4}-\d{4}',
            'suspicious_vendors': [
                'cash', 'personal', 'friend', 'family', 'test', 'demo'
            ],
            'high_frequency_vendors': 10,  # More than 10 invoices from same vendor in 30 days
            'unusual_times': ['00:00', '23:59'],  # Midnight transactions
            'suspicious_amounts': {
                'min': 0.01,
                'max': 10000.00,
                'round_threshold': 0.95  # 95% of amounts are round numbers
            }
        }
    
    def analyze_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze invoice for fraud indicators
        
        Args:
            invoice_data: Extracted invoice data
            
        Returns:
            Fraud analysis results
        """
        try:
            fraud_analysis = {
                'overall_score': 0.0,
                'flags': [],
                'details': {},
                'confidence': 0.0,
                'risk_level': 'low'
            }
            
            # Run individual fraud checks
            duplicate_score = self._check_duplicate_claims(invoice_data)
            inflation_score = self._check_inflated_expenses(invoice_data)
            ghost_vendor_score = self._check_ghost_vendor(invoice_data)
            split_billing_score = self._check_split_billing(invoice_data)
            pattern_score = self._check_suspicious_patterns(invoice_data)
            
            # Calculate overall fraud score
            scores = [duplicate_score, inflation_score, ghost_vendor_score, 
                     split_billing_score, pattern_score]
            fraud_analysis['overall_score'] = max(scores)
            
            # Add flags for significant scores
            if duplicate_score > self.thresholds['duplicate']:
                fraud_analysis['flags'].append('duplicate_claim')
            if inflation_score > self.thresholds['inflation']:
                fraud_analysis['flags'].append('inflated_expense')
            if ghost_vendor_score > self.thresholds['ghost_vendor']:
                fraud_analysis['flags'].append('ghost_vendor')
            if split_billing_score > self.thresholds['split_billing']:
                fraud_analysis['flags'].append('split_billing')
            if pattern_score > self.thresholds['suspicious_patterns']:
                fraud_analysis['flags'].append('suspicious_patterns')
            
            # Set risk level
            if fraud_analysis['overall_score'] > 0.8:
                fraud_analysis['risk_level'] = 'high'
            elif fraud_analysis['overall_score'] > 0.5:
                fraud_analysis['risk_level'] = 'medium'
            else:
                fraud_analysis['risk_level'] = 'low'
            
            # Calculate confidence based on data quality
            fraud_analysis['confidence'] = self._calculate_confidence(invoice_data)
            
            # Store detailed analysis
            fraud_analysis['details'] = {
                'duplicate_analysis': {
                    'score': duplicate_score,
                    'similar_invoices': self._find_similar_invoices(invoice_data)
                },
                'inflation_analysis': {
                    'score': inflation_score,
                    'category_average': self._get_category_average(invoice_data)
                },
                'ghost_vendor_analysis': {
                    'score': ghost_vendor_score,
                    'vendor_verification': self._verify_vendor(invoice_data)
                },
                'split_billing_analysis': {
                    'score': split_billing_score,
                    'related_transactions': self._find_related_transactions(invoice_data)
                },
                'pattern_analysis': {
                    'score': pattern_score,
                    'anomalies': self._detect_anomalies(invoice_data)
                }
            }
            
            logger.info("Fraud analysis completed", 
                       invoice_number=invoice_data.get('invoice_number'),
                       overall_score=fraud_analysis['overall_score'],
                       risk_level=fraud_analysis['risk_level'],
                       flags=fraud_analysis['flags'])
            
            return fraud_analysis
            
        except Exception as e:
            logger.error("Fraud analysis failed", error=str(e))
            return {
                'overall_score': 0.0,
                'flags': ['analysis_failed'],
                'details': {'error': str(e)},
                'confidence': 0.0,
                'risk_level': 'unknown'
            }
    
    def _check_duplicate_claims(self, invoice_data: Dict[str, Any]) -> float:
        """Check for duplicate claims"""
        try:
            vendor_name = invoice_data.get('vendor_name', '').lower()
            amount = invoice_data.get('total_amount') or invoice_data.get('amount')
            invoice_date = invoice_data.get('invoice_date')
            
            if not all([vendor_name, amount, invoice_date]):
                return 0.0
            
            # Find similar invoices from the same vendor
            similar_invoices = Invoice.query.filter(
                Invoice.vendor_name.ilike(f'%{vendor_name}%'),
                Invoice.total_amount == amount,
                Invoice.status == 'processed'
            ).all()
            
            if not similar_invoices:
                return 0.0
            
            # Check for exact duplicates
            for invoice in similar_invoices:
                if self._is_exact_duplicate(invoice_data, invoice):
                    return 1.0
            
            # Check for near duplicates using text similarity
            max_similarity = 0.0
            for invoice in similar_invoices:
                similarity = self._calculate_text_similarity(invoice_data, invoice)
                max_similarity = max(max_similarity, similarity)
            
            return max_similarity
            
        except Exception as e:
            logger.error("Duplicate check failed", error=str(e))
            return 0.0
    
    def _check_inflated_expenses(self, invoice_data: Dict[str, Any]) -> float:
        """Check for inflated expenses"""
        try:
            amount = invoice_data.get('total_amount') or invoice_data.get('amount')
            category = invoice_data.get('category')
            
            if not amount or not category:
                return 0.0
            
            # Get category average
            category_avg = self._get_category_average(invoice_data)
            if not category_avg:
                return 0.0
            
            # Calculate inflation ratio
            inflation_ratio = amount / category_avg
            
            # Score based on inflation ratio
            if inflation_ratio > 3.0:
                return 1.0
            elif inflation_ratio > 2.0:
                return 0.8
            elif inflation_ratio > 1.5:
                return 0.6
            else:
                return 0.0
                
        except Exception as e:
            logger.error("Inflation check failed", error=str(e))
            return 0.0
    
    def _check_ghost_vendor(self, invoice_data: Dict[str, Any]) -> float:
        """Check for ghost vendors"""
        try:
            vendor_name = invoice_data.get('vendor_name', '').lower()
            
            if not vendor_name:
                return 0.0
            
            # Check for suspicious vendor names
            for suspicious in self.suspicious_patterns['suspicious_vendors']:
                if suspicious in vendor_name:
                    return 0.9
            
            # Check vendor verification
            verification_score = self._verify_vendor(invoice_data)
            
            # Check for new vendors with high amounts
            vendor_history = Invoice.query.filter(
                Invoice.vendor_name.ilike(f'%{vendor_name}%')
            ).count()
            
            amount = invoice_data.get('total_amount') or invoice_data.get('amount', 0)
            
            if vendor_history == 0 and amount > 1000:
                return 0.7
            
            return verification_score
            
        except Exception as e:
            logger.error("Ghost vendor check failed", error=str(e))
            return 0.0
    
    def _check_split_billing(self, invoice_data: Dict[str, Any]) -> float:
        """Check for split billing fraud"""
        try:
            vendor_name = invoice_data.get('vendor_name', '').lower()
            amount = invoice_data.get('total_amount') or invoice_data.get('amount')
            invoice_date = invoice_data.get('invoice_date')
            
            if not all([vendor_name, amount, invoice_date]):
                return 0.0
            
            # Find related transactions from same vendor on same day
            related_invoices = Invoice.query.filter(
                Invoice.vendor_name.ilike(f'%{vendor_name}%'),
                Invoice.invoice_date == invoice_date,
                Invoice.status == 'processed'
            ).all()
            
            if len(related_invoices) < 2:
                return 0.0
            
            # Calculate combined amount
            combined_amount = sum(
                float(inv.total_amount or inv.amount or 0) 
                for inv in related_invoices
            )
            
            # Check if combined amount exceeds approval threshold
            if combined_amount > 5000:  # Example threshold
                return 0.9
            
            # Check for similar amounts (potential split)
            amounts = [float(inv.total_amount or inv.amount or 0) for inv in related_invoices]
            if len(set(amounts)) == 1:  # All amounts are the same
                return 0.8
            
            return 0.0
            
        except Exception as e:
            logger.error("Split billing check failed", error=str(e))
            return 0.0
    
    def _check_suspicious_patterns(self, invoice_data: Dict[str, Any]) -> float:
        """Check for suspicious patterns"""
        try:
            score = 0.0
            
            # Check for round amounts
            amount = invoice_data.get('total_amount') or invoice_data.get('amount')
            if amount and re.match(self.suspicious_patterns['round_amounts'], str(amount)):
                score += 0.3
            
            # Check for suspicious invoice numbers
            invoice_number = invoice_data.get('invoice_number', '')
            if re.search(self.suspicious_patterns['sequential_invoices'], invoice_number):
                score += 0.4
            
            # Check for unusual amounts
            if amount:
                if amount < self.suspicious_patterns['suspicious_amounts']['min']:
                    score += 0.5
                elif amount > self.suspicious_patterns['suspicious_amounts']['max']:
                    score += 0.3
            
            # Check for high frequency from same vendor
            vendor_name = invoice_data.get('vendor_name', '')
            if vendor_name:
                recent_count = self._count_recent_vendor_invoices(vendor_name)
                if recent_count > self.suspicious_patterns['high_frequency_vendors']:
                    score += 0.4
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error("Suspicious patterns check failed", error=str(e))
            return 0.0
    
    def _is_exact_duplicate(self, invoice_data: Dict[str, Any], existing_invoice: Invoice) -> bool:
        """Check if invoice is exact duplicate"""
        try:
            # Compare key fields
            if (invoice_data.get('vendor_name', '').lower() == 
                (existing_invoice.vendor_name or '').lower()):
                
                amount1 = invoice_data.get('total_amount') or invoice_data.get('amount')
                amount2 = existing_invoice.total_amount or existing_invoice.amount
                
                if amount1 and amount2 and abs(float(amount1) - float(amount2)) < 0.01:
                    return True
            
            return False
            
        except Exception as e:
            logger.error("Exact duplicate check failed", error=str(e))
            return False
    
    def _calculate_text_similarity(self, invoice_data: Dict[str, Any], existing_invoice: Invoice) -> float:
        """Calculate text similarity between invoices"""
        try:
            # Combine text fields for comparison
            text1 = ' '.join([
                invoice_data.get('description', ''),
                invoice_data.get('vendor_name', ''),
                str(invoice_data.get('amount', ''))
            ])
            
            text2 = ' '.join([
                existing_invoice.description or '',
                existing_invoice.vendor_name or '',
                str(existing_invoice.amount or '')
            ])
            
            if not text1 or not text2:
                return 0.0
            
            # Use TF-IDF for similarity
            texts = [text1, text2]
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return similarity
            
        except Exception as e:
            logger.error("Text similarity calculation failed", error=str(e))
            return 0.0
    
    def _get_category_average(self, invoice_data: Dict[str, Any]) -> Optional[float]:
        """Get average amount for invoice category"""
        try:
            category = invoice_data.get('category')
            if not category:
                return None
            
            # Get invoices from same category
            category_invoices = Invoice.query.filter(
                Invoice.category == category,
                Invoice.status == 'processed'
            ).all()
            
            if not category_invoices:
                return None
            
            # Calculate average
            amounts = [
                float(inv.total_amount or inv.amount or 0) 
                for inv in category_invoices
            ]
            
            return sum(amounts) / len(amounts) if amounts else None
            
        except Exception as e:
            logger.error("Category average calculation failed", error=str(e))
            return None
    
    def _verify_vendor(self, invoice_data: Dict[str, Any]) -> float:
        """Verify vendor legitimacy"""
        try:
            vendor_name = invoice_data.get('vendor_name', '').lower()
            
            # Simple verification based on name patterns
            if len(vendor_name) < 3:
                return 0.8  # Suspicious short names
            
            # Check for common business indicators
            business_indicators = ['inc', 'llc', 'corp', 'ltd', 'company', 'co']
            has_business_indicator = any(indicator in vendor_name for indicator in business_indicators)
            
            if not has_business_indicator:
                return 0.6  # No business indicators
            
            return 0.2  # Appears legitimate
            
        except Exception as e:
            logger.error("Vendor verification failed", error=str(e))
            return 0.5
    
    def _find_similar_invoices(self, invoice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar invoices"""
        try:
            vendor_name = invoice_data.get('vendor_name', '')
            amount = invoice_data.get('total_amount') or invoice_data.get('amount')
            
            if not vendor_name:
                return []
            
            similar_invoices = Invoice.query.filter(
                Invoice.vendor_name.ilike(f'%{vendor_name}%'),
                Invoice.status == 'processed'
            ).limit(5).all()
            
            return [inv.to_dict() for inv in similar_invoices]
            
        except Exception as e:
            logger.error("Similar invoices search failed", error=str(e))
            return []
    
    def _find_related_transactions(self, invoice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find related transactions for split billing analysis"""
        try:
            vendor_name = invoice_data.get('vendor_name', '')
            invoice_date = invoice_data.get('invoice_date')
            
            if not vendor_name or not invoice_date:
                return []
            
            related_invoices = Invoice.query.filter(
                Invoice.vendor_name.ilike(f'%{vendor_name}%'),
                Invoice.invoice_date == invoice_date,
                Invoice.status == 'processed'
            ).all()
            
            return [inv.to_dict() for inv in related_invoices]
            
        except Exception as e:
            logger.error("Related transactions search failed", error=str(e))
            return []
    
    def _count_recent_vendor_invoices(self, vendor_name: str) -> int:
        """Count recent invoices from vendor"""
        try:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            count = Invoice.query.filter(
                Invoice.vendor_name.ilike(f'%{vendor_name}%'),
                Invoice.created_at >= thirty_days_ago,
                Invoice.status == 'processed'
            ).count()
            
            return count
            
        except Exception as e:
            logger.error("Recent vendor invoice count failed", error=str(e))
            return 0
    
    def _detect_anomalies(self, invoice_data: Dict[str, Any]) -> List[str]:
        """Detect anomalies in invoice data"""
        anomalies = []
        
        try:
            # Check for missing required fields
            required_fields = ['vendor_name', 'amount', 'invoice_date']
            for field in required_fields:
                if not invoice_data.get(field):
                    anomalies.append(f'missing_{field}')
            
            # Check for unusual amounts
            amount = invoice_data.get('total_amount') or invoice_data.get('amount')
            if amount:
                if amount < 0.01:
                    anomalies.append('very_small_amount')
                elif amount > 10000:
                    anomalies.append('very_large_amount')
            
            # Check for future dates
            invoice_date = invoice_data.get('invoice_date')
            if invoice_date:
                try:
                    date_obj = datetime.strptime(invoice_date, '%Y-%m-%d').date()
                    if date_obj > datetime.now().date():
                        anomalies.append('future_date')
                except ValueError:
                    anomalies.append('invalid_date')
            
            return anomalies
            
        except Exception as e:
            logger.error("Anomaly detection failed", error=str(e))
            return ['detection_failed']
    
    def _calculate_confidence(self, invoice_data: Dict[str, Any]) -> float:
        """Calculate confidence in fraud analysis"""
        try:
            confidence = 1.0
            
            # Reduce confidence for missing data
            required_fields = ['vendor_name', 'amount', 'invoice_date', 'invoice_number']
            missing_fields = sum(1 for field in required_fields if not invoice_data.get(field))
            confidence -= missing_fields * 0.1
            
            # Reduce confidence for low-quality data
            if not invoice_data.get('description'):
                confidence -= 0.1
            
            if not invoice_data.get('category'):
                confidence -= 0.1
            
            return max(confidence, 0.0)
            
        except Exception as e:
            logger.error("Confidence calculation failed", error=str(e))
            return 0.5
