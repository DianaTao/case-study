"""Configuration management for the backend."""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Supabase
    supabase_url: str
    supabase_key: str
    
    # LLM (OpenAI)
    openai_api_key: str = ""
    
    # Server
    port: int = 8000
    host: str = "0.0.0.0"
    environment: str = "development"
    
    # CORS - can be set via environment variable (comma-separated) or defaults to localhost
    _allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
    allowed_origins: List[str] = (
        [origin.strip() for origin in _allowed_origins_env.split(",") if origin.strip()]
        if _allowed_origins_env
        else ["http://localhost:3000"]
    )
    
    # Supported appliances (config-based for extensibility)
    supported_appliances: List[str] = ["refrigerator", "dishwasher"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
