"""
NLP Extractor for parsing invoice data from text
"""

import re
import json
import spacy
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any
import structlog

logger = structlog.get_logger()

class NLPExtractor:
    """NLP extractor for parsing invoice data from extracted text"""
    
    def __init__(self):
        # Load spaCy model (you may need to download: python -m spacy download en_core_web_sm)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found, using basic regex extraction")
            self.nlp = None
        
        # Common invoice patterns
        self.patterns = {
            'invoice_number': [
                r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)',
                r'inv\s*#?\s*:?\s*([A-Z0-9\-]+)',
                r'bill\s*#?\s*:?\s*([A-Z0-9\-]+)',
                r'receipt\s*#?\s*:?\s*([A-Z0-9\-]+)',
                r'#\s*([A-Z0-9\-]+)'
            ],
            'amount': [
                r'total\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
                r'amount\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
                r'subtotal\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
                r'grand\s*total\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
                r'\$\s*([0-9,]+\.?[0-9]*)'
            ],
            'tax': [
                r'tax\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
                r'vat\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
                r'sales\s*tax\s*:?\s*\$?([0-9,]+\.?[0-9]*)'
            ],
            'date': [
                r'date\s*:?\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})',
                r'invoice\s*date\s*:?\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})',
                r'bill\s*date\s*:?\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})',
                r'([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})'
            ],
            'due_date': [
                r'due\s*date\s*:?\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})',
                r'payment\s*due\s*:?\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})'
            ]
        }
        
        # Common vendor patterns
        self.vendor_patterns = [
            r'from\s*:?\s*([A-Za-z\s&.,]+)',
            r'vendor\s*:?\s*([A-Za-z\s&.,]+)',
            r'company\s*:?\s*([A-Za-z\s&.,]+)',
            r'bill\s*to\s*:?\s*([A-Za-z\s&.,]+)'
        ]
        
        # Common categories
        self.categories = {
            'travel': ['travel', 'hotel', 'flight', 'taxi', 'uber', 'lyft', 'gas', 'fuel', 'parking'],
            'meals': ['restaurant', 'food', 'meal', 'dining', 'cafe', 'coffee', 'lunch', 'dinner'],
            'office': ['office', 'supplies', 'stationery', 'paper', 'pen', 'pencil', 'stapler'],
            'software': ['software', 'license', 'subscription', 'saas', 'cloud', 'hosting'],
            'hardware': ['computer', 'laptop', 'monitor', 'keyboard', 'mouse', 'printer'],
            'utilities': ['electricity', 'water', 'internet', 'phone', 'telephone', 'utility'],
            'marketing': ['advertising', 'marketing', 'promotion', 'social media', 'campaign'],
            'consulting': ['consulting', 'consultant', 'professional', 'service', 'expert']
        }
    
    def extract_invoice_data(self, text: str) -> Dict[str, Any]:
        """
        Extract structured invoice data from text
        
        Args:
            text: Raw text from OCR
            
        Returns:
            Dictionary containing extracted invoice data
        """
        try:
            if not text or not text.strip():
                return {}
            
            # Clean text
            cleaned_text = self._clean_text(text)
            
            # Extract basic information
            invoice_data = {
                'invoice_number': self._extract_invoice_number(cleaned_text),
                'vendor_name': self._extract_vendor_name(cleaned_text),
                'vendor_address': self._extract_vendor_address(cleaned_text),
                'amount': self._extract_amount(cleaned_text),
                'tax_amount': self._extract_tax_amount(cleaned_text),
                'total_amount': self._extract_total_amount(cleaned_text),
                'currency': self._extract_currency(cleaned_text),
                'invoice_date': self._extract_invoice_date(cleaned_text),
                'due_date': self._extract_due_date(cleaned_text),
                'description': self._extract_description(cleaned_text),
                'category': self._extract_category(cleaned_text),
                'line_items': self._extract_line_items(cleaned_text),
                'payment_method': self._extract_payment_method(cleaned_text),
                'notes': self._extract_notes(cleaned_text)
            }
            
            # Calculate total if not found
            if not invoice_data['total_amount'] and invoice_data['amount'] and invoice_data['tax_amount']:
                try:
                    amount = float(invoice_data['amount'])
                    tax = float(invoice_data['tax_amount'])
                    invoice_data['total_amount'] = amount + tax
                except (ValueError, TypeError):
                    pass
            
            # Clean up None values
            invoice_data = {k: v for k, v in invoice_data.items() if v is not None}
            
            logger.info("Invoice data extracted", 
                       invoice_number=invoice_data.get('invoice_number'),
                       vendor=invoice_data.get('vendor_name'),
                       amount=invoice_data.get('total_amount'))
            
            return invoice_data
            
        except Exception as e:
            logger.error("Invoice data extraction failed", error=str(e))
            return {}
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere
        text = re.sub(r'[^\w\s\.,\-\$@#:()]', '', text)
        return text.strip()
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number"""
        for pattern in self.patterns['invoice_number']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_vendor_name(self, text: str) -> Optional[str]:
        """Extract vendor name"""
        for pattern in self.vendor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                vendor = match.group(1).strip()
                # Clean up vendor name
                vendor = re.sub(r'\s+', ' ', vendor)
                return vendor[:100]  # Limit length
        return None
    
    def _extract_vendor_address(self, text: str) -> Optional[str]:
        """Extract vendor address"""
        # Look for address patterns
        address_patterns = [
            r'address\s*:?\s*([A-Za-z0-9\s,.\-]+)',
            r'location\s*:?\s*([A-Za-z0-9\s,.\-]+)',
            r'([0-9]+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln))'
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                address = match.group(1).strip()
                return address[:200]  # Limit length
        return None
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract main amount"""
        amounts = self._extract_all_amounts(text)
        if amounts:
            # Return the largest amount (likely the main amount)
            return max(amounts)
        return None
    
    def _extract_tax_amount(self, text: str) -> Optional[float]:
        """Extract tax amount"""
        for pattern in self.patterns['tax']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        return None
    
    def _extract_total_amount(self, text: str) -> Optional[float]:
        """Extract total amount"""
        total_patterns = [
            r'total\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
            r'grand\s*total\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
            r'amount\s*due\s*:?\s*\$?([0-9,]+\.?[0-9]*)'
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        return None
    
    def _extract_all_amounts(self, text: str) -> List[float]:
        """Extract all monetary amounts from text"""
        amounts = []
        amount_pattern = r'\$?([0-9,]+\.?[0-9]*)'
        
        for match in re.finditer(amount_pattern, text):
            try:
                amount = float(match.group(1).replace(',', ''))
                if 0 < amount < 1000000:  # Reasonable range
                    amounts.append(amount)
            except ValueError:
                continue
        
        return amounts
    
    def _extract_currency(self, text: str) -> str:
        """Extract currency"""
        currency_patterns = [
            r'USD|US\$|\$',
            r'EUR|€',
            r'GBP|£',
            r'CAD|C\$',
            r'AUD|A\$'
        ]
        
        for pattern in currency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if 'USD' in pattern or '$' in pattern:
                    return 'USD'
                elif 'EUR' in pattern or '€' in pattern:
                    return 'EUR'
                elif 'GBP' in pattern or '£' in pattern:
                    return 'GBP'
                elif 'CAD' in pattern:
                    return 'CAD'
                elif 'AUD' in pattern:
                    return 'AUD'
        
        return 'USD'  # Default
    
    def _extract_invoice_date(self, text: str) -> Optional[str]:
        """Extract invoice date"""
        for pattern in self.patterns['date']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                parsed_date = self._parse_date(date_str)
                if parsed_date:
                    return parsed_date.isoformat()
        return None
    
    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date"""
        for pattern in self.patterns['due_date']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                parsed_date = self._parse_date(date_str)
                if parsed_date:
                    return parsed_date.isoformat()
        return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        date_formats = [
            '%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y',
            '%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y',
            '%Y-%m-%d', '%Y/%m/%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract description or purpose"""
        # Look for common description patterns
        desc_patterns = [
            r'description\s*:?\s*([A-Za-z0-9\s,.\-]+)',
            r'purpose\s*:?\s*([A-Za-z0-9\s,.\-]+)',
            r'for\s*:?\s*([A-Za-z0-9\s,.\-]+)',
            r'business\s*purpose\s*:?\s*([A-Za-z0-9\s,.\-]+)'
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                return desc[:200]  # Limit length
        return None
    
    def _extract_category(self, text: str) -> Optional[str]:
        """Extract expense category"""
        text_lower = text.lower()
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        
        return None
    
    def _extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract line items from invoice"""
        line_items = []
        
        # Simple line item extraction (can be enhanced)
        lines = text.split('\n')
        for line in lines:
            # Look for lines with quantity, description, and amount
            line_item_pattern = r'(\d+)\s+([A-Za-z\s]+)\s+\$?([0-9,]+\.?[0-9]*)'
            match = re.search(line_item_pattern, line)
            if match:
                try:
                    quantity = int(match.group(1))
                    description = match.group(2).strip()
                    amount = float(match.group(3).replace(',', ''))
                    
                    line_items.append({
                        'quantity': quantity,
                        'description': description,
                        'amount': amount
                    })
                except (ValueError, IndexError):
                    continue
        
        return line_items
    
    def _extract_payment_method(self, text: str) -> Optional[str]:
        """Extract payment method"""
        payment_patterns = [
            r'credit\s*card',
            r'debit\s*card',
            r'cash',
            r'check',
            r'bank\s*transfer',
            r'paypal',
            r'venmo'
        ]
        
        text_lower = text.lower()
        for pattern in payment_patterns:
            if re.search(pattern, text_lower):
                return pattern.replace('\\s+', ' ').title()
        
        return None
    
    def _extract_notes(self, text: str) -> Optional[str]:
        """Extract notes or comments"""
        note_patterns = [
            r'notes?\s*:?\s*([A-Za-z0-9\s,.\-]+)',
            r'comments?\s*:?\s*([A-Za-z0-9\s,.\-]+)',
            r'remarks?\s*:?\s*([A-Za-z0-9\s,.\-]+)'
        ]
        
        for pattern in note_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                notes = match.group(1).strip()
                return notes[:300]  # Limit length
        return None
