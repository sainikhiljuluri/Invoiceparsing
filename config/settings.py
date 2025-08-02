"""
Configuration settings for the invoice processing system
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # AI Services
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229")
    
    # Application
    environment: str = os.getenv("ENVIRONMENT", "development")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Directories
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    processed_dir: Path = Path(os.getenv("PROCESSED_DIR", "./processed"))
    results_dir: Path = Path(os.getenv("RESULTS_DIR", "./results"))
    
    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields from .env

# Create global settings instance
settings = Settings()

# Create directories if they don't exist
settings.upload_dir.mkdir(exist_ok=True)
settings.processed_dir.mkdir(exist_ok=True)
settings.results_dir.mkdir(exist_ok=True)
