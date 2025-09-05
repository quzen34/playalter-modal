import logging
import logging.handlers
import sys
import os
from typing import Optional
from datetime import datetime
import json
import traceback

class ColoredFormatter(logging.Formatter):
    """Custom colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'processing_time'):
            log_entry['processing_time'] = record.processing_time
        
        return json.dumps(log_entry)

class PlayAlterLogger:
    """Centralized logging configuration for PLAYALTER platform."""
    
    def __init__(self, log_dir: str = "/tmp/logs"):
        self.log_dir = log_dir
        self.setup_log_directory()
        
    def setup_log_directory(self):
        """Create log directory if it doesn't exist."""
        os.makedirs(self.log_dir, exist_ok=True)
        
    def setup_logging(self, 
                     log_level: str = "INFO",
                     enable_console: bool = True,
                     enable_file: bool = True,
                     enable_json: bool = True,
                     max_file_size: int = 50 * 1024 * 1024,  # 50MB
                     backup_count: int = 5):
        """Setup comprehensive logging configuration."""
        
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Set log level
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger.setLevel(numeric_level)
        
        formatters = {
            'detailed': logging.Formatter(
                '[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ),
            'colored': ColoredFormatter(
                '[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ),
            'json': JSONFormatter()
        }
        
        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatters['colored'])
            console_handler.setLevel(numeric_level)
            root_logger.addHandler(console_handler)
        
        # Main log file handler
        if enable_file:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=os.path.join(self.log_dir, 'playalter.log'),
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatters['detailed'])
            file_handler.setLevel(numeric_level)
            root_logger.addHandler(file_handler)
        
        # JSON log file handler for structured logging
        if enable_json:
            json_handler = logging.handlers.RotatingFileHandler(
                filename=os.path.join(self.log_dir, 'playalter.json'),
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            json_handler.setFormatter(formatters['json'])
            json_handler.setLevel(numeric_level)
            root_logger.addHandler(json_handler)
        
        # Error log file (only errors and above)
        error_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(self.log_dir, 'errors.log'),
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatters['detailed'])
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
        
        # Performance log file
        perf_logger = logging.getLogger('performance')
        perf_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(self.log_dir, 'performance.log'),
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        perf_handler.setFormatter(formatters['json'])
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False  # Don't propagate to root logger
        
        # Security log file
        security_logger = logging.getLogger('security')
        security_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(self.log_dir, 'security.log'),
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        security_handler.setFormatter(formatters['json'])
        security_logger.addHandler(security_handler)
        security_logger.setLevel(logging.INFO)
        security_logger.propagate = False
        
        logging.info("Logging system initialized successfully")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name."""
        return logging.getLogger(name)
    
    def get_performance_logger(self) -> logging.Logger:
        """Get performance-specific logger."""
        return logging.getLogger('performance')
    
    def get_security_logger(self) -> logging.Logger:
        """Get security-specific logger."""
        return logging.getLogger('security')

class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)

def log_performance(operation: str, processing_time: float, 
                   user_id: Optional[str] = None, 
                   additional_data: Optional[dict] = None):
    """Log performance metrics."""
    perf_logger = logging.getLogger('performance')
    
    extra_data = {
        'operation': operation,
        'processing_time': processing_time
    }
    
    if user_id:
        extra_data['user_id'] = user_id
    
    if additional_data:
        extra_data.update(additional_data)
    
    perf_logger.info(f"Operation completed: {operation}", extra=extra_data)

def log_security_event(event_type: str, user_id: Optional[str] = None,
                      ip_address: Optional[str] = None, 
                      additional_data: Optional[dict] = None):
    """Log security events."""
    security_logger = logging.getLogger('security')
    
    extra_data = {
        'event_type': event_type
    }
    
    if user_id:
        extra_data['user_id'] = user_id
    
    if ip_address:
        extra_data['ip_address'] = ip_address
    
    if additional_data:
        extra_data.update(additional_data)
    
    security_logger.warning(f"Security event: {event_type}", extra=extra_data)

def log_api_request(method: str, endpoint: str, user_id: Optional[str] = None,
                   processing_time: Optional[float] = None,
                   status_code: Optional[int] = None,
                   error: Optional[str] = None):
    """Log API requests."""
    logger = logging.getLogger('api')
    
    extra_data = {
        'method': method,
        'endpoint': endpoint
    }
    
    if user_id:
        extra_data['user_id'] = user_id
    
    if processing_time:
        extra_data['processing_time'] = processing_time
    
    if status_code:
        extra_data['status_code'] = status_code
    
    if error:
        extra_data['error'] = error
        logger.error(f"API request failed: {method} {endpoint}", extra=extra_data)
    else:
        logger.info(f"API request: {method} {endpoint}", extra=extra_data)

class ErrorHandler:
    """Centralized error handling utilities."""
    
    @staticmethod
    def handle_service_error(service_name: str, operation: str, error: Exception, 
                           user_id: Optional[str] = None) -> dict:
        """Handle service errors consistently."""
        logger = logging.getLogger(f'services.{service_name}')
        
        error_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S') + f"_{hash(str(error)) % 10000:04d}"
        
        error_data = {
            'error_id': error_id,
            'service': service_name,
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        
        if user_id:
            error_data['user_id'] = user_id
        
        logger.error(f"Service error in {service_name}.{operation}", 
                    extra=error_data, exc_info=True)
        
        return {
            'success': False,
            'error': f"Service error occurred. Error ID: {error_id}",
            'error_id': error_id
        }
    
    @staticmethod
    def handle_validation_error(field: str, message: str, value: any = None) -> dict:
        """Handle validation errors."""
        logger = logging.getLogger('validation')
        
        error_data = {
            'validation_field': field,
            'validation_message': message
        }
        
        if value is not None:
            error_data['invalid_value'] = str(value)
        
        logger.warning(f"Validation error: {field} - {message}", extra=error_data)
        
        return {
            'success': False,
            'error': f"Validation failed: {message}",
            'field': field
        }

# Global logger instance
playalter_logger = PlayAlterLogger()

# Setup default logging configuration
def setup_default_logging():
    """Setup default logging configuration for PLAYALTER."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_dir = os.getenv('LOG_DIR', '/tmp/logs')
    
    global playalter_logger
    playalter_logger = PlayAlterLogger(log_dir)
    playalter_logger.setup_logging(log_level=log_level)

# Initialize logging when module is imported
setup_default_logging()