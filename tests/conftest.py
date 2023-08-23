import os
import pytest
from pydantic_settings import BaseSettings
import logging
import sys
import re
from urllib.parse import urlparse, parse_qs

import requests
import requests_mock
from rq import SimpleWorker, Queue
from fastapi.testclient import TestClient
from fakeredis import FakeStrictRedis
from api.server import app, get_redis
from lib.settings import settings


# class TestEnvironment(BaseSettings):
#     LIVE: bool = False
#     TA1_UNIFIED_URL: str = "https://ta1:5"
#     MIT_TR_URL: str = "https://mit:10"
#     TDS_URL: str = "https://tds:15"
#     OPENAI_API_KEY: str = "foo"
#     LOG_LEVEL: str = "INFO"


# @pytest.fixture
# def environment():
#     yield TestEnvironment()


@pytest.fixture(autouse=True)
def loghandler():
    LOG_LEVEL = settings.LOG_LEVEL.upper()
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


@pytest.fixture
def http_mock():
    # adapter = requests_mock.Adapter()
    # session = requests.Session()
    # session.mount('mock://', adapter)
    with requests_mock.Mocker(real_http=False) as mocker:#, session=session) as mocker:
        yield mocker


@pytest.fixture
def file_storage(http_mock):
    storage = {}

    def get_filename(url):
        return parse_qs(urlparse(url).query)["filename"][0]

    def get_loc(request, _):
        filename = get_filename(request.url)
        return {"url": f"mock://filesave?filename={filename}"}

    def save(request, context):
        filename = get_filename(request.url)
        storage[filename] = request.body.read().decode("utf-8")
        return {"status": "success"}

    def retrieve(filename):
        return storage.get(filename, storage)

    def retrieve_from_url(request, _):
        retrieve(get_filename(request.url)).encode()

    get_file_url = re.compile(f"(?:(?:upload)|(?:download))-url")
    http_mock.get(get_file_url, json=get_loc)
    file_url = re.compile("filesave")
    http_mock.put(file_url, json=save)
    http_mock.get(file_url, content=retrieve_from_url)

    yield retrieve
