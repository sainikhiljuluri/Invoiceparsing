"""
Main entry point for the Invoice Processing System
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from config.logging_config import setup_logging

# Setup logging
logger = setup_logging(settings.log_level)

def main():
    """Main application entry point"""
    logger.info("=" * 50)
    logger.info("Invoice Processing System Starting...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Upload Directory: {settings.upload_dir}")
    logger.info(f"Processed Directory: {settings.processed_dir}")
    logger.info(f"Results Directory: {settings.results_dir}")
    logger.info("=" * 50)
    
    # Component status check
    components = {
        "Environment Setup": True,
        "Database Configuration": False,
        "PDF Extraction": False,
        "Vendor Detection": False,
        "Product Data Loader": False,
        "Claude AI Processing": False,
        "Product Matching": False,
        "Price Updates": False,
        "Processing Pipeline": False,
        "Advanced RAG System": False
    }
    
    logger.info("\nComponent Status:")
    for component, status in components.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"{status_icon} {component}")
    
    logger.info("\nSystem ready for component development!")

if __name__ == "__main__":
    main()
