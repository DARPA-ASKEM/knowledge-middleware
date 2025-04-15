import os
from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict

# Patch AWS Key Names
prod_names = {
    "AWS_PROD_ACCESS_KEY_ID": "AWS_ACCESS_KEY_ID",
    "AWS_PROD_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY",
    "AWS_PROD_BUCKET": "BUCKET",
}

for from_var, to_var in prod_names.items():
    value = os.environ.get(from_var, None)
    if value:
        os.environ[to_var] = value


class ExtractionServices(Enum):
    COSMOS: str = "cosmos"
    SKEMA: str = "skema"


class Settings(BaseSettings):
    MOCK_TA1: bool = True
    MOCK_TDS: bool = True
    REDIS_HOST: str = "redis.knowledge-middleware"
    REDIS_PORT: int = 6379
    TA1_UNIFIED_URL: str = "https://api.askem.lum.ai"
    SKEMA_RS_URL: str = "http://skema-rs.staging.terarium.ai"
    MIT_TR_URL: str = "http://mit-tr.staging.terarium.ai"
    TDS_URL: str = "http://data-service.staging.terarium.ai:8000"
    TDS_USER: str = "user"
    TDS_PASSWORD: str = "password"
    COSMOS_URL: str = "http://cosmos0004.chtc.wisc.edu:8088"
    OPENAI_API_KEY: str = "foo"
    LOG_LEVEL: str = "INFO"
    PDF_EXTRACTOR: ExtractionServices = "cosmos"
    AWS_ACCESS_KEY_ID: str = "NA"
    AWS_SECRET_ACCESS_KEY: str = "NA"
    BUCKET: str = "NA"


settings = Settings()
