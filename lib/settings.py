from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LIVE: bool = False
    REDIS_HOST: str = "redis.ta1-service"
    REDIS_PORT: int = 6379
    TA1_UNIFIED_URL: str = "mock://ta1:5"
    SKEMA_RS_URL: str = "mock://skema-rs.staging.terarium.ai"
    MIT_TR_URL: str = "mock://mit:10"
    TDS_URL: str = "mock://tds:15"
    OPENAI_API_KEY: str = "foo"
    LOG_LEVEL: str = "INFO"


settings = Settings()