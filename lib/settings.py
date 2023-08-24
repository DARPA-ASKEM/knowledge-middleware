from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LIVE: bool = False
    REDIS_HOST: str = "redis.ta1-service"
    REDIS_PORT: int = 6379
    TA1_UNIFIED_URL: str = "http://ta1:5"
    SKEMA_RS_URL: str = "http://skema-rs.staging.terarium.ai"
    MIT_TR_URL: str = "http://mit:10"
    TDS_URL: str = "http://tds:15"
    OPENAI_API_KEY: str = "foo"
    LOG_LEVEL: str = "INFO"


settings = Settings()