"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SmartParkingPlatform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # PostgreSQL
    POSTGRES_USER: str = "parking_admin"
    POSTGRES_PASSWORD: str = "parking_secret_123"
    POSTGRES_DB: str = "smart_parking"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j_parking_123"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Azure
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_SYNAPSE_CONNECTION_STRING: Optional[str] = None

    # ML
    MODEL_PATH: str = "./ml/models"
    YOLO_MODEL: str = "yolov8n.pt"
    CONFIDENCE_THRESHOLD: float = 0.5
    TESSERACT_CMD: str = "/usr/bin/tesseract"

    # Camera
    CAMERA_FEED_URL: str = "rtsp://localhost:8554/parking"
    FRAME_SKIP: int = 5
    MAX_CAMERAS: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
