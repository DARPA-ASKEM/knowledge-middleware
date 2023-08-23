import os
import pytest
from pydantic_settings import BaseSettings
import logging
import sys
import re
from urllib.parse import urlparse, parse_qs, quote_plus 
import json
from io import BytesIO

import requests

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


@pytest.fixture
def context_dir(request):
    chosen = request.node.get_closest_marker("resource").args[0]
    yield f"./tests/resources/{chosen}" 


@pytest.fixture(autouse=True)
def tds(context_dir, http_mock, file_storage):
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"

    # Mock the TDS artifact
    artifact = {
        "id": "artifact-123",
        "name": "paper",
        "description": "test paper",
        "timestamp": "2023-07-17T19:11:43",
        "file_names": ["paper.pdf"],
        "metadata": {"text": text},
    }
    artifact_url = f"{settings.TDS_URL}/artifacts/{artifact['id']}"
    http_mock.get(artifact_url, json=artifact)
    http_mock.put(artifact_url)
    content = BytesIO("some encoded PDF content goes here".encode())
    requests.put(f"mock://filesave?filename={quote_plus('paper.pdf')}", content)


@pytest.fixture(autouse=True)
def ta1(context_dir, http_mock, tds):
    extractions = json.load(open(f"{context_dir}/extractions.json"))
    http_mock.post(f"{settings.TA1_UNIFIED_URL}/text-reading/integrated-text-extractions?annotate_skema=True&annotate_mit=True", json=extractions)
