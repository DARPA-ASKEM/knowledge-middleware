import os
import pytest
from pydantic_settings import BaseSettings
import logging
import sys

from rq import SimpleWorker, Queue
from fastapi.testclient import TestClient
from fakeredis import FakeStrictRedis
from api.server import app, get_redis


class TestEnvironment(BaseSettings):
    LIVE: bool = False
    TA1_UNIFIED_URL: str = "https://ta1:5"
    MIT_TR_URL: str = "http://mit:10"
    TDS_URL: str = "http://tds:15"
    OPENAI_API_KEY: str = "foo"
    LOG_LEVEL: str = "INFO"


@pytest.fixture
def environment():
    yield TestEnvironment()


@pytest.fixture(autouse=True)
def loghandler(environment):
    LOG_LEVEL = environment.LOG_LEVEL.upper()
    numeric_level = getattr(logging, LOG_LEVEL, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {LOG_LEVEL}")

    logger = logging.getLogger(__name__)
    logger.setLevel(numeric_level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(lineno)d] - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@pytest.fixture
def redis():
    return FakeStrictRedis()


@pytest.fixture
def worker(redis):
    queue = Queue(connection=redis, default_timeout=-1)
    return SimpleWorker([queue], connection=redis)


@pytest.fixture
def client(redis):
    app.dependency_overrides[get_redis] = lambda: redis
    yield TestClient(app)
    app.dependency_overrides[get_redis] = get_redis
