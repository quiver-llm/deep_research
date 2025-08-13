"""
Configuration management for the Dify pipeline.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""
    model_config: SettingsConfigDict = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    # Dify API settings
    DIFY_BASE_URL: str = Field(
        default=os.getenv("DIFY_BASE_URL", "http://localhost/v1"),
        description="Base URL for the Dify API"
    )
    DIFY_API_KEY: str = Field(
        default=os.getenv("DIFY_API_KEY", ""),
        description="API key for Dify authentication"
    )
    DIFY_USER: str = Field(
        default=os.getenv("DIFY_USER", ""),
        description="User identifier for Dify"
    )
    
    # OpenWebUI settings
    OPENWEBUI_BASE_URL: str = Field(
        default=os.getenv("OPENWEBUI_BASE_URL", "http://localhost:3000"),
        description="Base URL for the OpenWebUI API"
    )
    OPENWEBUI_API_KEY: str = Field(
        default=os.getenv("OPENWEBUI_API_KEY", ""),
        description="API key for OpenWebUI authentication"
    )
    
    # Application settings
    DEBUG: bool = Field(
        default=os.getenv("DEBUG", "false").lower() == "true",
        description="Enable debug mode"
    )
    LOG_LEVEL: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # File handling
    UPLOAD_DIR: str = Field(
        default=os.getenv("UPLOAD_DIR", "/tmp/dify_uploads"),
        description="Directory for storing uploaded files"
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=int(os.getenv("MAX_UPLOAD_SIZE", "10485760")),  # 10MB default
        description="Maximum file upload size in bytes"
    )
    
    # Timeouts
    API_TIMEOUT: int = Field(
        default=int(os.getenv("API_TIMEOUT", "30")),
        description="Timeout for API requests in seconds"
    )
    
    @field_validator("UPLOAD_DIR")
    def validate_upload_dir(cls, v: str) -> str:
        """Ensure upload directory exists and is writable."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        
        if not os.access(v, os.W_OK):
            raise ValueError(f"Upload directory is not writable: {v}")
            
        return str(path.absolute())
    
    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        v = v.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {', '.join(valid_levels)}")
        return v


def get_settings() -> Settings:
    """Get the application settings."""
    return Settings()


def get_pipeline_config() -> dict:
    """Get the pipeline configuration from settings."""
    settings = get_settings()
    
    return {
        "dify_base_url": settings.DIFY_BASE_URL,
        "dify_api_key": settings.DIFY_API_KEY,
        "openwebui_base_url": settings.OPENWEBUI_BASE_URL,
        "openwebui_api_key": settings.OPENWEBUI_API_KEY,
        "debug": settings.DEBUG
    }
