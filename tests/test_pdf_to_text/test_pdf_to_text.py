import json
from unittest.mock import Mock, patch
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../..", "workers"))

# Create a test application
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)

# Create a fake redis server and a fake redis instance
from fakeredis import FakeStrictRedis
from rq import Queue

queue = Queue(is_async=False, connection=FakeStrictRedis())


# Note that the patches have to be in reverse order of the
# test function arguments
@patch("requests.put")  # patch anytime a PUT is made
@patch("requests.get")  # patch anytime a GET is made
@patch("requests.post")  # patch anytime a POST is made
@patch("api.utils.get_queue", return_value=queue)  # mock the redis queue
def test_pdf_to_text(mock_queue, mock_post, mock_get, mock_put):
    # The mock responses

    # Mock the TDS artifact
    mock_tds_artifact = Mock()
    artifact_id = "artifact-123"
    artifact = {
        "id": artifact_id,
        "name": "paper",
        "description": "test paper",
        "timestamp": "2023-07-17T19:11:43",
        "file_names": ["paper.pdf"],
        "metadata": {},
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

    # Mock the downloaded code
    mock_paper = Mock()
    mock_paper.content = "some encoded PDF content goes here".encode()
    mock_paper.status_code = 200

    # Mock all gets with side effects
    mock_get.side_effect = [mock_tds_artifact, mock_presigned_download_url, mock_paper]

    mock_ta1_response = Mock()
    text = json.loads(open("tests/test_pdf_to_text/text.json").read())
    mock_ta1_response.json.return_value = text
    mock_ta1_response.text = json.dumps(text)
    mock_ta1_response.status_code = 200

    # Mock all posts with side effects
    mock_post.side_effect = [mock_ta1_response]

    # Mock the TDS artifact
    mock_updated_tds_artifact = Mock()
    artifact["text"] = "extracted pdf text content here"
    mock_updated_tds_artifact.json.return_value = artifact
    mock_updated_tds_artifact.text = json.dumps(artifact)
    mock_updated_tds_artifact.status_code = 200

    # Mock all puts with side effects
    mock_put.side_effect = [mock_updated_tds_artifact]

    # Define the query parameters
    query_params = {"artifact_id": artifact_id}

    # Call the endpoint
    response = client.post(
        "/pdf_to_text",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()
    print(results)

    # Assert the status code and response
    assert response.status_code == 200
    assert results.get("status") == "finished"
    assert results.get("job_error") == None
    assert results.get("result", {}).get("job_result") == {
        "extraction_status_code": mock_ta1_response.status_code,
        "extraction": mock_ta1_response.json(),
        "tds_status_code": mock_updated_tds_artifact.status_code,
    }
