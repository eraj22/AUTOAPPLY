from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # App
    app_name: str = "AutoApply"
    debug: bool = os.getenv("DEBUG", "False") == "True"
    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:3000")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://autoapply:autoapply_dev_password@localhost:5432/autoapply_db")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Ollama
    ollama_api_url: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    
    # JWT
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 48
    
    # Email (Resend)
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    email_from: str = os.getenv("EMAIL_FROM", "noreply@autoapply.dev")
    
    # Scraping
    scrape_interval_hours: int = int(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))
    
    # Job Matching
    fit_score_threshold: int = int(os.getenv("FIT_SCORE_THRESHOLD", "65"))
    auto_apply_threshold: int = int(os.getenv("AUTO_APPLY_THRESHOLD", "75"))
    
    # Application Mode
    application_mode: str = os.getenv("APPLICATION_MODE", "approval")  # approval or auto_apply
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()
