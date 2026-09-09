from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.4-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
