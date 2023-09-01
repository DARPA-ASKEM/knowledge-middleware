import os
import pytest
from pydantic_settings import BaseSettings
import logging
import sys
import re
from urllib.parse import urlparse, parse_qs, quote_plus 
import json
from collections import namedtuple
from io import BytesIO
from itertools import count

import requests
import requests_mock
from rq import SimpleWorker, Queue
from fastapi.testclient import TestClient
from fakeredis import FakeStrictRedis
from api.server import app, get_redis
from worker.utils import SESSION
from lib.settings import settings


class StrictMocker(requests_mock.Mocker):
    def register_uri(self, *args, **kwargs):
        url = args[1] if isinstance(args[1], str) else args[1].pattern
        if "http://" in url or "https://" in url:
            return

        kwargs['_real_http'] = kwargs.pop('real_http', False)
        kwargs.setdefault('json_encoder', self._json_encoder)
        return self._adapter.register_uri(*args, **kwargs)


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
    adapter = requests_mock.Adapter()
    SESSION.mount('mock://', adapter)
    with StrictMocker(real_http=True, session=SESSION) as mocker:
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
        return storage[filename]

    def retrieve_from_url(request, _):
        return retrieve(get_filename(request.url)).encode()

    def upload(filename, content):
        if isinstance(content, dict):
            content = json.dumps(content)
        if isinstance(content, str):
            content = BytesIO(content.encode())
        SESSION.put(f"mock://filesave?filename={quote_plus(filename)}", content)

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
    def generate(code=False):
        if code:
            _type = "code"
        else:
            _type = "artifacts"
        artifact = {
            "id": f"{_type}-{next(counter)}",
            "name": _type,
            "description": f"test {_type}",
            "timestamp": "2023-07-17T19:11:43",
            "metadata": {},
        }
        if code:
            artifact["filename"] = "code.py"
            artifact["language"] = "python"
        else:
            artifact["file_names"]: []
        artifact_url = f"{settings.TDS_URL}/{_type}/{artifact['id']}"
        http_mock.get(artifact_url, json=artifact)
        http_mock.put(artifact_url)
        return artifact
    return generate
