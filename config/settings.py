import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import json
from enum import Enum

class EnvironmentType(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class ModelConfig:
    """Model configuration settings."""
    flame_model_path: str = "/tmp/flame_model"
    inswapper_model_path: str = "/tmp/inswapper_models"
    face_detector_model: str = "buffalo_l"
    max_face_detection_size: tuple = (640, 640)
    
    # FLAME model parameters
    n_shape_params: int = 300
    n_expression_params: int = 100
    n_pose_params: int = 15
    
    # Processing parameters
    max_image_size: tuple = (4096, 4096)
    min_image_size: tuple = (64, 64)
    default_jpeg_quality: int = 95

class SecurityConfig:
    """Security configuration settings."""
    jwt_secret_key: str = Field(default_factory=lambda: os.urandom(32).hex())
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour
    
    # File upload limits
    max_file_size_mb: int = 10
    max_batch_size: int = 10
    
    # API key settings
    api_key_length: int = 32
    api_key_prefix: str = "pk_"
    
    # Password requirements
    min_password_length: int = 8
    require_special_chars: bool = True

class DatabaseConfig:
    """Database configuration (placeholder for future implementation)."""
    database_url: str = "sqlite:///playalter.db"
    echo_sql: bool = False
    pool_size: int = 10
    max_overflow: int = 20

class CacheConfig:
    """Cache configuration."""
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 3600
    max_cache_size_mb: int = 512

class PlayAlterSettings(BaseModel):
    """Main application settings."""
    
    # Environment
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    app_name: str = "PLAYALTER Platform"
    app_version: str = "1.0.0"
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Modal.com configuration
    modal_app_name: str = "playalter-platform"
    modal_environment: str = "main"
    gpu_type: str = "T4"
    memory_mb: int = 16384
    timeout_seconds: int = 3600
    keep_warm: int = 1
    max_concurrent_inputs: int = 10
    
    # Directories
    upload_dir: str = "/tmp/uploads"
    log_dir: str = "/tmp/logs"
    model_cache_dir: str = "/tmp/model_cache"
    
    # Logging
    log_level: str = "INFO"
    enable_file_logging: bool = True
    enable_json_logging: bool = True
    max_log_file_size_mb: int = 50
    log_backup_count: int = 5
    
    # CORS settings
    cors_origins: List[str] = ["*"]
    cors_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: List[str] = ["*"]
    
    # Feature flags
    enable_face_analysis: bool = True
    enable_privacy_masks: bool = True
    enable_face_swap: bool = True
    enable_batch_processing: bool = True
    enable_3d_mesh_export: bool = False
    enable_video_processing: bool = False
    
    # Performance settings
    max_processing_time_seconds: int = 300
    max_queue_size: int = 100
    cleanup_temp_files: bool = True
    temp_file_max_age_hours: int = 24
    
    # Monitoring
    enable_metrics: bool = True
    metrics_endpoint: str = "/metrics"
    health_check_endpoint: str = "/health"
    
    # Model configurations
    model: ModelConfig = Field(default_factory=ModelConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    
    @field_validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @field_validator('cors_origins')
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return [v]
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }

class ConfigManager:
    """Manage application configuration."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self._settings = None
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from environment and files."""
        if self.config_file and os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Set environment variables from config file
            for key, value in self._flatten_dict(config_data).items():
                os.environ[key.upper()] = str(value)
        
        self._settings = PlayAlterSettings()
    
    def _flatten_dict(self, d: dict, parent_key: str = '', sep: str = '__') -> dict:
        """Flatten nested dictionary for environment variables."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    @property
    def settings(self) -> PlayAlterSettings:
        """Get current settings."""
        return self._settings
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split('.')
        value = self._settings
        
        try:
            for k in keys:
                value = getattr(value, k)
            return value
        except (AttributeError, KeyError):
            return default
    
    def get_model_config(self) -> ModelConfig:
        """Get model configuration."""
        return self._settings.model
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return self._settings.security
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self._settings.database
    
    def get_cache_config(self) -> CacheConfig:
        """Get cache configuration."""
        return self._settings.cache
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self._settings.environment == EnvironmentType.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self._settings.environment == EnvironmentType.PRODUCTION
    
    def save_config(self, file_path: str):
        """Save current configuration to file."""
        config_dict = self._settings.dict()
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
    
    def update_setting(self, key: str, value: Any):
        """Update a configuration setting dynamically."""
        keys = key.split('.')
        obj = self._settings
        
        # Navigate to parent object
        for k in keys[:-1]:
            obj = getattr(obj, k)
        
        # Set the final value
        setattr(obj, keys[-1], value)
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Check required directories
        dirs_to_check = [
            self._settings.upload_dir,
            self._settings.log_dir,
            self._settings.model_cache_dir
        ]
        
        for dir_path in dirs_to_check:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    issues.append(f"Cannot create directory {dir_path}: {str(e)}")
        
        # Check GPU settings for Modal
        if self._settings.gpu_type not in ["T4", "A10G", "A100"]:
            issues.append(f"Invalid GPU type: {self._settings.gpu_type}")
        
        # Check memory settings
        if self._settings.memory_mb < 4096:
            issues.append("Memory setting too low for AI models (minimum 4GB recommended)")
        
        # Check file size limits
        if self._settings.security.max_file_size_mb > 100:
            issues.append("File size limit too high, may cause memory issues")
        
        return issues
    
    def get_modal_image_config(self) -> Dict[str, Any]:
        """Get Modal image configuration."""
        return {
            "python_version": "3.11",
            "gpu": self._settings.gpu_type,
            "memory": self._settings.memory_mb,
            "timeout": self._settings.timeout_seconds,
            "keep_warm": self._settings.keep_warm,
            "allow_concurrent_inputs": self._settings.max_concurrent_inputs
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            "level": self._settings.log_level,
            "log_dir": self._settings.log_dir,
            "enable_file": self._settings.enable_file_logging,
            "enable_json": self._settings.enable_json_logging,
            "max_file_size": self._settings.max_log_file_size_mb * 1024 * 1024,
            "backup_count": self._settings.log_backup_count
        }

# Global configuration manager
config_manager = ConfigManager()

# Convenience function to get settings
def get_settings() -> PlayAlterSettings:
    """Get application settings."""
    return config_manager.settings

def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value."""
    return config_manager.get(key, default)

# Environment-specific configurations
def get_development_config() -> Dict[str, Any]:
    """Get development-specific configuration overrides."""
    return {
        "debug": True,
        "log_level": "DEBUG",
        "cors_origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "enable_metrics": True,
        "gpu_type": "T4",  # Use smaller GPU for development
        "memory_mb": 8192,
        "keep_warm": 0  # Don't keep warm in development
    }

def get_production_config() -> Dict[str, Any]:
    """Get production-specific configuration overrides."""
    return {
        "debug": False,
        "log_level": "INFO",
        "cors_origins": ["https://playalter.com"],
        "enable_metrics": True,
        "gpu_type": "A100",  # Use powerful GPU for production
        "memory_mb": 24576,
        "keep_warm": 2,
        "max_concurrent_inputs": 20
    }

def load_config_from_file(file_path: str) -> ConfigManager:
    """Load configuration from JSON file."""
    return ConfigManager(config_file=file_path)

def create_default_config_file(file_path: str):
    """Create a default configuration file."""
    default_config = {
        "app_name": "PLAYALTER Platform",
        "environment": "development",
        "debug": True,
        "log_level": "INFO",
        "model": {
            "flame_model_path": "/tmp/flame_model",
            "inswapper_model_path": "/tmp/inswapper_models",
            "max_image_size": [4096, 4096],
            "min_image_size": [64, 64]
        },
        "security": {
            "max_file_size_mb": 10,
            "max_batch_size": 10,
            "rate_limit_requests": 100,
            "access_token_expire_minutes": 30
        }
    }
    
    with open(file_path, 'w') as f:
        json.dump(default_config, f, indent=2)

# Initialize configuration validation on import
def validate_startup_config():
    """Validate configuration on startup."""
    issues = config_manager.validate_config()
    if issues:
        print("Configuration issues detected:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Configuration validation passed")

# Run validation if this module is imported
if __name__ != "__main__":
    validate_startup_config()