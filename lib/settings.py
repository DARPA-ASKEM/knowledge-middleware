from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MOCK_TA1: bool = True
    MOCK_TDS: bool = True
    REDIS_HOST: str = "redis.knowledge-middleware"
    REDIS_PORT: int = 6379
    TA1_UNIFIED_URL: str = "http://ta1:5"
    SKEMA_RS_URL: str = "http://skema-rs.staging.terarium.ai"
    MIT_TR_URL: str = "http://mit:10"
    TDS_URL: str = "http://tds:15"
    OPENAI_API_KEY: str = "foo"
    LOG_LEVEL: str = "INFO"
    AWS_ACCESS_KEY_ID: str = "NA"
    AWS_SECRET_ACCESS_KEY: str = "NA"
    BUCKET: str = "NA"


settings = Settings()
