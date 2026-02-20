from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/towdyouso"
    UPLOAD_DIR: str = "uploads"
    BASE_URL: str = "http://localhost:8000"

    model_config = {"env_file": ".env"}


settings = Settings()
