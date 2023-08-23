import os
import json
import pytest
from io import BytesIO
from urllib.parse import quote_plus

import requests

from lib.settings import settings

CONTEXT_DIR = "./tests/test_pdf_extractions" 

@pytest.fixture(autouse=True)
def tds(http_mock, file_storage):
    text_json = json.load(open(f"{CONTEXT_DIR}/text.json"))
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
def ta1(http_mock, tds):
    extractions = json.load(open(f"{CONTEXT_DIR}/extractions.json"))
    http_mock.post(f"{settings.TA1_UNIFIED_URL}/text-reading/integrated-text-extractions?annotate_skema=True&annotate_mit=True", json=extractions)
