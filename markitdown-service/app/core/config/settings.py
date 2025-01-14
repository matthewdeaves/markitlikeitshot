from pydantic_settings import BaseSettings
from pydantic import ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import os
from functools import lru_cache
import logging

class LoggingConfig:
    """Logging configuration container"""
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0

    LEVEL_MAP = {
        "CRITICAL": CRITICAL,
        "ERROR": ERROR,
        "WARNING": WARNING,
        "INFO": INFO,
        "DEBUG": DEBUG,
        "NOTSET": NOTSET,
    }

class Settings(BaseSettings):
    # Pydantic V2 configuration
    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8"
    )

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "MarkItDown API"
    VERSION: str = "1.0.0"
    
    # File Processing Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB default
    SUPPORTED_EXTENSIONS: List[str] = [
        '.pdf', '.docx', '.pptx', '.xlsx', '.wav', '.mp3',
        '.jpg', '.jpeg', '.png', '.html', '.htm', '.txt', '.csv', '.json', '.xml'
    ]
    
    # Request Settings
    REQUEST_TIMEOUT: int = 10  # seconds
    USER_AGENT: str = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/91.0.4472.124 Safari/537.36'
    )

    # Rate Limiting Settings
    RATE_LIMITING_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_RATE: int = 30  # requests
    RATE_LIMIT_DEFAULT_PERIOD: int = 60  # seconds
    
    # Test-specific rate limiting settings
    TEST_RATE_LIMIT_DEFAULT_RATE: int = 5  # requests
    TEST_RATE_LIMIT_DEFAULT_PERIOD: int = 5  # seconds
    
    # Endpoint-specific rate limits
    RATE_LIMITS: Dict[str, Dict[str, int]] = {
        "/api/v1/convert/url": {"rate": 60, "per": 60},
        "/api/v1/convert/file": {"rate": 60, "per": 60},
        "/api/v1/convert/text": {"rate": 60, "per": 60}
    }

    # Endpoints excluded from rate limiting
    RATE_LIMIT_EXCLUDED_ENDPOINTS: List[str] = [
        "/api/v1/admin/*"
    ]

    # CORS Settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]

    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///./{ENVIRONMENT}_api_keys.db"
    )
    DATABASE_CONNECT_ARGS: dict = {"check_same_thread": False}
    DATABASE_POOL_SIZE: int = 5
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_ECHO: bool = ENVIRONMENT == "development"

    # API Key Authentication Settings
    API_KEY_AUTH_ENABLED: bool = True
    API_KEY_HEADER_NAME: str = "X-API-Key"
    API_KEY_LENGTH: int = 32
    ADMIN_API_KEY: Optional[str] = os.getenv("ADMIN_API_KEY")
    API_KEY_EXPIRATION_DAYS: Optional[int] = None

    # Initial Setup Settings
    INITIAL_ADMIN_NAME: str = os.getenv("INITIAL_ADMIN_NAME", "System Admin")
    INITIAL_ADMIN_EMAIL: str = os.getenv(
        "INITIAL_ADMIN_EMAIL", 
        "admin@example.com"
    )

    # Security Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")

    # Enhanced Logging Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    LOG_DIR: str = "logs"
    LOG_FILE_PREFIX: str = "app"
    LOG_FILE_SUFFIX: str = ".log"
    LOG_ROTATION: str = "midnight"
    LOG_BACKUP_COUNT: int = 7
    LOG_ENCODING: str = "utf-8"

    # Log Retention Settings
    LOG_RETENTION_DAYS: Dict[str, int] = {
        "audit": 90,  # Using existing AUDIT_LOG_RETENTION_DAYS
        "app": 30,    # Application logs
        "cli": 15,    # CLI operation logs
        "sql": 7      # Database query logs
    }
    
    # Log Rotation Settings
    LOG_ROTATION_MAX_SIZE: str = "100M"  # Rotate when file exceeds this size
    LOG_COMPRESSION_ENABLED: bool = True
    LOG_COMPRESSION_METHOD: str = "gzip"
    
    # Environment-specific retention multipliers
    LOG_RETENTION_MULTIPLIERS: Dict[str, float] = {
        "development": 0.5,  # Keep logs for half the time in development
        "test": 0.25,        # Keep logs for quarter the time in test
        "production": 1.0    # Keep logs for full duration in production
    }

    # Component-specific logging levels
    COMPONENT_LOG_LEVELS: Dict[str, str] = {
        "uvicorn": "INFO",
        "uvicorn.error": "INFO",
        "uvicorn.access": "INFO",
        "sqlalchemy.engine": "WARNING",
        "sqlalchemy.pool": "WARNING",
        "sqlalchemy.dialects": "WARNING",
        "sqlalchemy.orm": "WARNING",
        "asyncio": "WARNING",
        "fastapi": "INFO",
        "app.api": "DEBUG",
        "app.core": "INFO",
        "app.db": "INFO",
        "app.cli": "INFO",
    }

    # Audit Log Settings
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_FILE: str = f"logs/audit_{ENVIRONMENT}.log"
    AUDIT_LOG_RETENTION_DAYS: int = 90
    AUDIT_LOG_LEVEL: str = "INFO"  # Audit logs should typically stay at INFO

    # API Documentation Settings
    DOCS_URL: Optional[str] = "/docs" if ENVIRONMENT != "production" else None
    REDOC_URL: Optional[str] = "/redoc" if ENVIRONMENT != "production" else None
    OPENAPI_URL: Optional[str] = "/openapi.json" if ENVIRONMENT != "production" else None

    # CLI Tool Settings
    CLI_COLORS: bool = True
    CLI_TABLE_STYLE: str = "rounded"

    @property
    def get_log_level(self) -> int:
        """Get the numeric log level, with environment-specific defaults"""
        env_levels = {
            "development": "DEBUG",
            "test": "WARNING",
            "production": "INFO"
        }
        
        # Use LOG_LEVEL from env, fall back to environment-specific default
        level_name = self.LOG_LEVEL.upper() or env_levels.get(self.ENVIRONMENT, "INFO")
        return LoggingConfig.LEVEL_MAP.get(level_name, LoggingConfig.INFO)

    def get_retention_days(self, log_type: str) -> int:
        """Get environment-adjusted retention period for log type"""
        base_days = self.LOG_RETENTION_DAYS.get(log_type, 30)
        multiplier = self.LOG_RETENTION_MULTIPLIERS.get(self.ENVIRONMENT, 1.0)
        return int(base_days * multiplier)

    def get_component_log_level(self, component: str) -> int:
        """Get log level for specific component"""
        if component in self.COMPONENT_LOG_LEVELS:
            return LoggingConfig.LEVEL_MAP.get(
                self.COMPONENT_LOG_LEVELS[component].upper(),
                self.get_log_level
            )
        return self.get_log_level

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

settings = get_settings()

__all__ = ["settings", "get_settings"]
