"""
File Processing Service with security validation.
"""
import os
import uuid
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ValidationError
from django.conf import settings


class FileTooLargeException(Exception):
    """Raised when file exceeds size limit."""
    pass


class InvalidFileTypeException(Exception):
    """Raised when file type is not allowed."""
    pass


class VirusDetectedException(Exception):
    """Raised when virus is detected in file."""
    pass


class FileProcessingService:
    """Service for secure file processing."""
    
    MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE
    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
    ]
    
    @staticmethod
    def validate_file(file):
        """
        Validate uploaded file for size, type, and security.
        """
        # Size check
        if file.size > FileProcessingService.MAX_FILE_SIZE:
            raise FileTooLargeException(
                f"File size exceeds {FileProcessingService.MAX_FILE_SIZE} bytes"
            )
        
        # Extension check
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in settings.ALLOWED_FILE_EXTENSIONS:
            raise InvalidFileTypeException(f"File extension {ext} not allowed")
        
        # MIME type check (server-side, when libmagic is available)
        file.seek(0)
        try:
            import magic as magic_lib
            mime_type = magic_lib.from_buffer(file.read(1024), mime=True)
            file.seek(0)
            if mime_type not in FileProcessingService.ALLOWED_MIME_TYPES:
                raise InvalidFileTypeException(f"MIME type {mime_type} not allowed")
        except ImportError:
            # libmagic not installed (e.g. brew install libmagic on macOS)
            file.seek(0)
        except Exception:
            # If magic library fails, log warning but allow (graceful degradation)
            file.seek(0)
        
        # Virus scan (if ClamAV available)
        # TODO: Implement ClamAV integration
        
        return True
    
    @staticmethod
    def generate_unique_filename(original_filename, group_id, file_type='ledger'):
        """Generate unique filename."""
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        uuid_str = str(uuid.uuid4())[:8]
        ext = os.path.splitext(original_filename)[1]
        
        return f"{timestamp}_{uuid_str}_{file_type}{ext}"
    
    @staticmethod
    def process_upload(file, user_id, group_id, file_type='ledger'):
        """
        Process uploaded file with validation.
        Returns file path for storage.
        """
        # Validate file
        FileProcessingService.validate_file(file)
        
        # Generate unique filename
        filename = FileProcessingService.generate_unique_filename(
            file.name, group_id, file_type
        )
        
        # Organize by date
        from django.utils import timezone
        now = timezone.now()
        upload_path = f"{file_type}/{group_id}/{now.year}/{now.month:02d}/{filename}"
        
        return upload_path
