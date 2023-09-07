from enum import Enum
from pydantic_settings import BaseSettings


class ExtractionServices(Enum):
    COSMOS: str = "cosmos"
    SKEMA: str = "skema"


class Settings(BaseSettings):
    MOCK_TA1: bool = True
    MOCK_TDS: bool = True
    REDIS_HOST: str = "redis.knowledge-middleware"
    REDIS_PORT: int = 6379
    TA1_UNIFIED_URL: str = "http://ta1:5"
    SKEMA_RS_URL: str = "http://skema-rs.staging.terarium.ai"
    MIT_TR_URL: str = "http://mit:10"
    TDS_URL: str = "http://tds:15"
    COSMOS_URL: str = "http://xdd.wisc.edu/cosmos_service"
    OPENAI_API_KEY: str = "foo"
    LOG_LEVEL: str = "INFO"
    PDF_EXTRACTOR: ExtractionServices = "cosmos"



settings = Settings()
