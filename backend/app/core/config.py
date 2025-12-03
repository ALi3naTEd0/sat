"""
Core Configuration Settings
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Gestor Fiscal Personal"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/sat_app"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_DB: int = 1
    
    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_SECRET_KEY: str = "change-this-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Encryption
    ENCRYPTION_KEY: str = "change-this-encryption-key"
    DOCUMENT_ENCRYPTION_SALT: str = "change-this-salt"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # File Storage
    STORAGE_TYPE: str = "local"  # local, s3, minio
    STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 10
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"
    
    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET_NAME: str = "sat-documents"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/2"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/3"
    
    # SAT Integration
    SAT_BASE_URL: str = "https://www.sat.gob.mx"
    SAT_PORTAL_URL: str = "https://portalcfdi.facturaelectronica.sat.gob.mx"
    SAT_TIMEOUT_SECONDS: int = 30
    SAT_MAX_RETRIES: int = 3
    
    # Automation
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000
    HEADLESS_BROWSER: bool = True
    SELENIUM_TIMEOUT: int = 30
    
    # OCR
    OCR_ENGINE: str = "tesseract"
    GOOGLE_VISION_API_KEY: str = ""
    TESSERACT_PATH: str = "/usr/bin/tesseract"
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@gestorfiscal.mx"
    
    # SMS
    SMS_PROVIDER: str = "twilio"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # Monitoring
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # PAC Integration
    PAC_ENABLED: bool = False
    PAC_PROVIDER: str = ""
    PAC_API_KEY: str = ""
    PAC_API_URL: str = ""

    model_config = SettingsConfigDict(
        env_file="../.env",
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()
