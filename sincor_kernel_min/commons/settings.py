from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    nats_url: str = "nats://localhost:4222"
    ollama_url: str = "http://localhost:11434"
    model_fallback: str = "stub"

    class Config:
        env_file = ".env"

settings = Settings()
