import os
import sys
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from config.logging_config import setup_logging

def test_environment_variables_loaded():
    """Test that environment variables are loaded"""
    # Check if .env file exists
    env_path = Path(".env")
    assert env_path.exists(), ".env file not found"
    
    # Check critical settings (won't check actual values for security)
    assert hasattr(settings, 'supabase_url')
    assert hasattr(settings, 'anthropic_api_key')
    assert hasattr(settings, 'claude_model')

def test_directories_created():
    """Test that required directories are created"""
    assert settings.upload_dir.exists()
    assert settings.processed_dir.exists()
    assert settings.results_dir.exists()

def test_logging_setup():
    """Test logging configuration"""
    logger = setup_logging("INFO")
    assert logger is not None
    
    # Test log file creation
    log_file = Path("logs/application.log")
    
    # Log a test message
    logger.info("Test log message")
    
    # Check if log file was created
    assert log_file.exists()

def test_python_version():
    """Test Python version compatibility"""
    assert sys.version_info >= (3, 8), "Python 3.8+ required"

def test_required_packages():
    """Test that required packages can be imported"""
    required_packages = [
        'fastapi',
        'supabase',
        'anthropic',
        'pdfplumber',
        'pandas',
        'sentence_transformers'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            pytest.fail(f"Required package '{package}' not installed")

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
