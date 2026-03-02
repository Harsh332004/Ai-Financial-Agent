from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # JWT Auth
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # News API
    NEWS_API_KEY: str = ""

    # File paths
    UPLOAD_DIR: str = "uploads"
    INDEX_DIR: str = "indexes"
    REPORTS_DIR: str = "reports"

    # Models
    EMBED_MODEL: str = "all-MiniLM-L6-v2"
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # RAG settings
    CHUNK_SIZE: int = 300
    CHUNK_OVERLAP: int = 50
    TOP_K_INITIAL: int = 10
    TOP_K_FINAL: int = 3
    MAX_HISTORY: int = 6

    # CORS
    FRONTEND_ORIGIN: str = Field(default="http://localhost:8501")


settings = Settings()

