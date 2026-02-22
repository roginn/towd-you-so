from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.2"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/towdyouso"
    UPLOAD_DIR: str = "uploads"
    BASE_URL: str = "http://localhost:8000"
    ROBOFLOW_API_KEY: str = ""
    ROBOFLOW_WORKFLOW_URL: str = "https://detect.roboflow.com/infer/workflows/mock-workspace/mock-parking-sign-ocr"

    model_config = {"env_file": ".env"}


settings = Settings()
