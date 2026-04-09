from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "FinNews Hunter API"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # MongoDB Settings
    MONGODB_IP: str = "localhost"
    MONGODB_PORT: int = 27017
    MONGODB_USERNAME: str = ""
    MONGODB_PASSWORD: str = ""
    
    # Project Paths
    PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    SRC_PATH: str = os.path.join(PROJECT_ROOT, "src")
    
    # Crawler Settings
    CONCURRENT_REQUESTS: int = 50
    DOWNLOAD_DELAY: int = 1
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
