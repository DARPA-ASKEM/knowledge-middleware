import json
from unittest.mock import Mock, patch
import os
import requests
import sys

import logging

logger = logging.getLogger(__name__)

sys.path.append(os.path.join(os.path.dirname(__file__), "../..", "workers"))

# Create a test application
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)

# Create a fake redis server and a fake redis instance
from fakeredis import FakeStrictRedis
from rq import Queue

queue = Queue(is_async=False, connection=FakeStrictRedis())

live = os.environ.get("LIVE", "FALSE")

##############################
##### The mock responses #####
##############################

text_json = json.loads(open("tests/test_pdf_extractions/text.json").read())
text = ""
for d in text_json:
    text += f"{d['content']}\n"

# Mock the TDS artifact
mock_tds_artifact = Mock()
artifact_id = "artifact-123"
artifact = {
    "id": artifact_id,
    "name": "paper",
    "description": "test paper",
    "timestamp": "2023-07-17T19:11:43",
    "file_names": ["paper.pdf"],
    "metadata": {"text": text},
}
mock_tds_artifact.json.return_value = artifact
mock_tds_artifact.text = json.dumps(artifact)
mock_tds_artifact.status_code = 200

# Mock the pre-signed download URL
mock_presigned_download_url = Mock()
mock_presigned_download_url.json.return_value = {
    "url": "http://localhost:1000",
    "method": "GET",
}

# Mock the downloaded paper
mock_paper = Mock()
mock_paper.content = "some encoded PDF content goes here".encode()
mock_paper.status_code = 200

mock_ta1_response = Mock()
extractions = json.loads(open("tests/test_pdf_extractions/extractions.json").read())
mock_ta1_response.json.return_value = extractions
mock_ta1_response.text = json.dumps(extractions)
mock_ta1_response.status_code = 200

# Mock the TDS artifact
mock_updated_tds_artifact = Mock()
ex = extractions["outputs"][0]["data"]
ex["text"] = text
artifact["metadata"] = ex
mock_updated_tds_artifact.json.return_value = artifact
mock_updated_tds_artifact.text = json.dumps(artifact)
mock_updated_tds_artifact.status_code = 200

#######################################
##### Setup for Integration Tests #####
#######################################

original_post = requests.post


def decide_post_response(*args, **kwargs):
    """
    This function redefines `requests.post` and optionally allows for overrides
    to be sent out (e.g. to TA1 live service) for true integration testing.
    """
    url = args[0]  # Assuming the first argument to requests.post is the URL
    if "ta1" in url:
        logger.info("Mocking response from TA1")
        return mock_ta1_response
    elif live == "TRUE":
        logger.info("Sending request to LIVE TA1 Service")
        return original_post(*args, **kwargs)  # Call the original


# Note that the patches have to be in reverse order of the
# test function arguments
@patch("requests.put")  # patch anytime a PUT is made
@patch("requests.get")  # patch anytime a GET is made
@patch(
    "requests.post", side_effect=decide_post_response
)  # patch anytime a POST is made
@patch("api.utils.get_queue", return_value=queue)  # mock the redis queue
def test_pdf_extractions(mock_queue, mock_post, mock_get, mock_put):
    # Mock all gets with side effects
    mock_get.side_effect = [mock_tds_artifact, mock_presigned_download_url, mock_paper]

    # Mock all puts with side effects
    mock_put.side_effect = [mock_updated_tds_artifact]

    # Define the query parameters
    query_params = {
        "artifact_id": artifact_id,
        "annotate_skema": True,
        "annotate_mit": True,
        "name": None,
        "description": None,
    }

    # Call the endpoint
    response = client.post(
        "/pdf_extractions",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()

    # Assert the status code and response
    assert response.status_code == 200
    assert results.get("status") == "finished", results.get("result", {}).get(
        "job_error"
    )
    assert results.get("result", {}).get("job_error") == None

    if live == "FALSE":
        assert results.get("result", {}).get("job_result") == {
            "extraction_status_code": mock_ta1_response.status_code,
            "extraction": [extractions["outputs"][0]["data"]],
            "tds_status_code": mock_updated_tds_artifact.status_code,
            "error": None,
        }
