from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    MINIO_ENDPOINT: str
    MINIO_PUBLIC_ENDPOINT: str = ""  # public-facing endpoint; defaults to MINIO_ENDPOINT if empty
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "automl-files"
    MINIO_USE_SSL: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ENVIRONMENT: str = "development"
    MAX_UPLOAD_SIZE_MB: int = 100
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    class Config:
        env_file = ".env"


settings = Settings()
