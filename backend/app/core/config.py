from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "case_sensitive": False}

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "perfume"
    DB_PASSWORD: str = "perfume_dev"
    DB_NAME: str = "perfume"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "perfume_dev"

    # Redis
    REDIS_URL: str = "redis://:perfume_dev@localhost:6379"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # App
    DEBUG: bool = False

    # LLM (OpenAI-compatible API)
    LLM_API_KEY: str = ""  # Set via env; empty = use template fallback
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TIMEOUT: float = 8.0  # seconds — shared by emotion (2s) + copy (5s)

    @property
    def pg_dsn(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
