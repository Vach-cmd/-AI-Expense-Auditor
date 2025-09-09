"""
OCR Engine for text extraction from images and PDFs
"""

import os
import io
import cv2
import numpy as np
from PIL import Image
import pytesseract
import fitz  # PyMuPDF for PDF processing
import structlog
from typing import Optional, List

logger = structlog.get_logger()

class OCREngine:
    """OCR engine for extracting text from various file formats"""
    
    def __init__(self):
        # Configure Tesseract path (adjust for your system)
        self.tesseract_config = '--oem 3 --psm 6'
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.pdf']
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """
        Extract text from file
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text or None if extraction fails
        """
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                return self._extract_from_image(file_path)
            else:
                logger.warning("Unsupported file format", file_path=file_path, format=file_ext)
                return None
                
        except Exception as e:
            logger.error("OCR extraction failed", file_path=file_path, error=str(e))
            return None
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Try text extraction first
                page_text = page.get_text()
                if page_text.strip():
                    text += page_text + "\n"
                else:
                    # If no text, convert page to image and use OCR
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    ocr_text = self._ocr_image(img)
                    if ocr_text:
                        text += ocr_text + "\n"
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            logger.error("PDF text extraction failed", file_path=file_path, error=str(e))
            return ""
    
    def _extract_from_image(self, file_path: str) -> str:
        """Extract text from image file"""
        try:
            # Load image
            image = cv2.imread(file_path)
            if image is None:
                logger.error("Could not load image", file_path=file_path)
                return ""
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)
            
            # Convert to PIL Image for Tesseract
            pil_image = Image.fromarray(cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB))
            
            # Extract text
            text = self._ocr_image(pil_image)
            return text
            
        except Exception as e:
            logger.error("Image text extraction failed", file_path=file_path, error=str(e))
            return ""
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            logger.error("Image preprocessing failed", error=str(e))
            return image
    
    def _ocr_image(self, image: Image.Image) -> str:
        """Perform OCR on PIL Image"""
        try:
            # Use Tesseract to extract text
            text = pytesseract.image_to_string(
                image, 
                config=self.tesseract_config,
                lang='eng'
            )
            return text.strip()
            
        except Exception as e:
            logger.error("OCR processing failed", error=str(e))
            return ""
    
    def extract_text_with_confidence(self, file_path: str) -> dict:
        """
        Extract text with confidence scores
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with text and confidence information
        """
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.pdf':
                return self._extract_from_pdf_with_confidence(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                return self._extract_from_image_with_confidence(file_path)
            else:
                return {'text': '', 'confidence': 0.0, 'error': 'Unsupported format'}
                
        except Exception as e:
            logger.error("OCR extraction with confidence failed", file_path=file_path, error=str(e))
            return {'text': '', 'confidence': 0.0, 'error': str(e)}
    
    def _extract_from_image_with_confidence(self, file_path: str) -> dict:
        """Extract text from image with confidence scores"""
        try:
            image = cv2.imread(file_path)
            if image is None:
                return {'text': '', 'confidence': 0.0, 'error': 'Could not load image'}
            
            processed_image = self._preprocess_image(image)
            pil_image = Image.fromarray(cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB))
            
            # Get text with confidence data
            data = pytesseract.image_to_data(
                pil_image, 
                config=self.tesseract_config,
                lang='eng',
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Extract text
            text = pytesseract.image_to_string(pil_image, config=self.tesseract_config, lang='eng')
            
            return {
                'text': text.strip(),
                'confidence': avg_confidence / 100.0,  # Convert to 0-1 scale
                'word_count': len([word for word in data['text'] if word.strip()])
            }
            
        except Exception as e:
            logger.error("Image OCR with confidence failed", file_path=file_path, error=str(e))
            return {'text': '', 'confidence': 0.0, 'error': str(e)}
    
    def _extract_from_pdf_with_confidence(self, file_path: str) -> dict:
        """Extract text from PDF with confidence scores"""
        try:
            text = ""
            total_confidence = 0.0
            page_count = 0
            
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                
                if page_text.strip():
                    text += page_text + "\n"
                    # For PDF text, assume high confidence
                    total_confidence += 0.9
                else:
                    # Convert to image and use OCR
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    ocr_result = self._extract_from_image_with_confidence(img)
                    if ocr_result['text']:
                        text += ocr_result['text'] + "\n"
                        total_confidence += ocr_result['confidence']
                
                page_count += 1
            
            doc.close()
            
            avg_confidence = total_confidence / page_count if page_count > 0 else 0.0
            
            return {
                'text': text.strip(),
                'confidence': avg_confidence,
                'page_count': page_count
            }
            
        except Exception as e:
            logger.error("PDF OCR with confidence failed", file_path=file_path, error=str(e))
            return {'text': '', 'confidence': 0.0, 'error': str(e)}
