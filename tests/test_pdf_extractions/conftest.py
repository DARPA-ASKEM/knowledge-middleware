import os
import json
import pytest
from io import BytesIO
from urllib.parse import quote_plus

import requests

from lib.settings import settings

CONTEXT_DIR = "./tests/test_pdf_extractions" 

@pytest.fixture(autouse=True)
def tds(http, file_storage):
    text_json = json.loads(open(f"{CONTEXT_DIR}/text.json").read())
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"

    # Mock the TDS artifact
    artifact_id = "artifact-123"
    artifact = {
        "id": artifact_id,
        "name": "paper",
        "description": "test paper",
        "timestamp": "2023-07-17T19:11:43",
        "file_names": ["paper.pdf"],
        "metadata": {"text": text},
    }
    http.get(f"{settings.TDS_URL}/artifacts/artifact-123", json=artifact)
    if settings.TDS_URL[:7] == "mock://":
        content = BytesIO("some encoded PDF content goes here".encode())
        requests.put(f"mock://filesave?filename={quote_plus('paper.pdf')}", content)


# def ta1():
#     mock_ta1_response = Mock()
#     extractions = json.loads(open("tests/test_pdf_extractions/extractions.json").read())
#     mock_ta1_response.json.return_value = extractions
#     mock_ta1_response.text = json.dumps(extractions)
#     mock_ta1_response.status_code = 200

#     # Mock the TDS artifact
#     mock_updated_tds_artifact = Mock()
#     ex = extractions["outputs"][0]["data"]
#     ex["text"] = text
#     artifact["metadata"] = ex
#     mock_updated_tds_artifact.json.return_value = artifact
#     mock_updated_tds_artifact.text = json.dumps(artifact)
#     mock_updated_tds_artifact.status_code = 200
