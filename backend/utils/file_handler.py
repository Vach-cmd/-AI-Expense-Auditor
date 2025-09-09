"""
File handling utilities for AI Expense Auditor
"""

import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
import structlog

logger = structlog.get_logger()

class FileHandler:
    """File handling utilities"""
    
    def __init__(self):
        self.allowed_extensions = {
            'pdf', 'jpg', 'jpeg', 'png', 'tiff', 'bmp', 
            'docx', 'xlsx', 'json', 'txt'
        }
    
    def is_allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        if not filename:
            return False
        
        file_ext = self._get_file_extension(filename)
        return file_ext.lower() in self.allowed_extensions
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension"""
        return os.path.splitext(filename)[1]
    
    def save_file(self, file, filename: str) -> str:
        """Save uploaded file"""
        try:
            # Generate unique filename
            file_ext = self._get_file_extension(filename)
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            
            # Ensure upload directory exists
            upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            
            logger.info("File saved successfully", 
                       original_filename=filename,
                       saved_path=file_path)
            
            return file_path
            
        except Exception as e:
            logger.error("File save failed", 
                        filename=filename, 
                        error=str(e))
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from filesystem"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("File deleted successfully", file_path=file_path)
                return True
            return False
            
        except Exception as e:
            logger.error("File deletion failed", 
                        file_path=file_path, 
                        error=str(e))
            return False
    
    def get_file_info(self, file_path: str) -> dict:
        """Get file information"""
        try:
            if not os.path.exists(file_path):
                return {}
            
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'extension': self._get_file_extension(file_path)
            }
            
        except Exception as e:
            logger.error("Get file info failed", 
                        file_path=file_path, 
                        error=str(e))
            return {}
    
    def validate_file_size(self, file_path: str, max_size: int = None) -> bool:
        """Validate file size"""
        try:
            if not max_size:
                max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16777216)
            
            file_size = os.path.getsize(file_path)
            return file_size <= max_size
            
        except Exception as e:
            logger.error("File size validation failed", 
                        file_path=file_path, 
                        error=str(e))
            return False
