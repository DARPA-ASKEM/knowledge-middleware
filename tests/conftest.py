import os
import pytest
from pydantic_settings import BaseSettings
import logging
import sys
import re
from urllib.parse import urlparse, parse_qs, quote_plus
import json
import time
from collections import namedtuple
from io import BytesIO
from itertools import count

import requests

import requests
import requests_mock
from rq import SimpleWorker, Queue
from fastapi.testclient import TestClient
from fakeredis import FakeStrictRedis
from api.server import app, get_redis
from lib.settings import settings


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
def context_dir(resource):
    yield f"./tests/scenarios/{resource}"


@pytest.fixture
def http_mock():
    # adapter = requests_mock.Adapter()
    # session = requests.Session()
    # session.mount('mock://', adapter)
    with requests_mock.Mocker(
        real_http=True
    ) as mocker:  # , session=session) as mocker:
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
        storage[filename] = request.body.read()
        return {"status": "success"}

    def retrieve(filename):
        return storage[filename]

    def retrieve_from_url(request, _):
        return retrieve(get_filename(request.url))

    def upload(filename, content):
        if isinstance(content, dict):
            content = json.dumps(content)
        if isinstance(content, str):
            content = BytesIO(content.encode())
        requests.put(f"mock://filesave?filename={quote_plus(filename)}", content)

    get_file_url = re.compile(f"(?:(?:upload)|(?:download))-url")
    http_mock.get(get_file_url, json=get_loc)
    file_url = re.compile("filesave")
    http_mock.put(file_url, json=save)
    http_mock.get(file_url, content=retrieve_from_url)
    Storage = namedtuple("Storage", ["retrieve", "upload"])

    yield Storage(retrieve=retrieve, upload=upload)


@pytest.fixture
def gen_tds_artifact(context_dir, http_mock, file_storage):
    # Mock the TDS artifact
    counter = count()

    def generate(code=False, dynamics_only=False, **extra_params):
        if code:
            _type = "code-asset"
        else:
            _type = "document-asset"
        artifact = {
            "id": f"{_type}-{next(counter)}",
            "name": _type,
            "description": f"test {_type}",
            "timestamp": "2023-07-17T19:11:43",
            "metadata": {},
            "username": "n/a",
        }
        if code:
            if dynamics_only:
                with open(f"{context_dir}/dynamics.json", "r") as f:
                    dynamics = json.load(f)
            else:
                dynamics = {}
            code_file = {
                "dynamics": dynamics,
                "language": "python",
            }
            artifact["files"] = {"code.py": code_file}
        else:
            artifact["file_names"] = []

        # Override any defaults or extend with provided extra params
        artifact.update(extra_params)

        if settings.MOCK_TDS:
            artifact_url = f"{settings.TDS_URL}/{_type}/{artifact['id']}"
            http_mock.get(artifact_url, json=artifact)
            http_mock.put(artifact_url)
        else:
            result = requests.post(f"{settings.TDS_URL}/{_type}", json=artifact)
            artifact["id"] = result.json()["id"]
            if result.status_code >= 400:
                raise requests.HTTPError("Error adding generated artifact to TDS")

        return artifact

    return generate


@pytest.fixture
def gen_tds_model(context_dir, http_mock):
    # Mock the TDS artifact
    counter = count()

    def generate(model_id=None, amr=None):
        if settings.MOCK_TDS:
            models_url = f"{settings.TDS_URL}/models"
            http_mock.post(models_url, json={"id": model_id})
        else:
            result = requests.post(f"{settings.TDS_URL}/models", json=amr)
            if result.status_code >= 400:
                raise requests.HTTPError("Error adding generated artifact to TDS")
            else:
                model_id = result.json()["id"]

        return model_id

    return generate


@pytest.mark.tryfirst
def pytest_runtest_protocol(item, nextitem):
    """
    Runs between tests, add a sleep to introduce delay when
    making external calls
    """
    if not settings.MOCK_TA1:
        if nextitem:  # Check if there's a next item
            time.sleep(90)  # Sleep for 60 seconds
