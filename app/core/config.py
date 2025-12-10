from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Diamond ERP API"
    DEBUG: bool = True


    # Mongo
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "diamond_erp"


    # JWT
    SECRET_KEY: str = Field(..., min_length=16)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"


    # Admin seed
    ADMIN_EMAIL: str = "admin@diamonderp.com"
    ADMIN_PASSWORD: str = "Admin@123"
    ADMIN_NAME: str = "Administrator"


    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password123"
    MINIO_USE_TLS: bool = False


    class Config:
        env_file = ".env"
        extra = "ignore"


    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()