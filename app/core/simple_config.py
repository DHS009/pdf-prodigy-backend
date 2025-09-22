"""
Simplified configuration for basic integration
"""

import os
from pathlib import Path

class Settings:
    # App Configuration
    APP_NAME: str = "PDF Prodigy API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    
    # File Upload Configuration
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: list = ["pdf"]
    
    # CORS Configuration
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ALLOWED_HOSTS: list = ["localhost", "127.0.0.1"]
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"

# Create global settings instance
settings = Settings()

# Create upload directory if it doesn't exist
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
