from pydantic_settings import BaseSettings, SettingsConfigDict
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
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://staging.gac.powerbrainlabs.com,http://146.148.68.124:3000"

    # Backend URL for image proxy and file serving
    BACKEND_URL: str = "https://backend-sta.gac.powerbrainlabs.com"

    # Super Admin seed
    SUPER_ADMIN_EMAIL: str = "superadmin@diamonderp.com"
    SUPER_ADMIN_PASSWORD: str = "SuperAdmin@123"
    SUPER_ADMIN_NAME: str = "Super Administrator"


    # Admin seed
    ADMIN_EMAIL: str = "admin@diamonderp.com"
    ADMIN_PASSWORD: str = "Admin@123"
    ADMIN_NAME: str = "Administrator"


    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password123"
    MINIO_USE_TLS: bool = False

    # Background Removal API
    REMBG_API_URL: str = "https://begon.webeazzy.com/api/process-image"
    REMBG_API_KEY: str

    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), extra="ignore")


    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()