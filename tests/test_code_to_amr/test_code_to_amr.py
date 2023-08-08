import json
from unittest.mock import Mock, patch, DEFAULT
import os
import requests
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


##############################
##### The mock responses #####
##############################

# Mock the TDS artifact
mock_tds_artifact = Mock()
artifact_id = "artifact-123"
artifact = {
    "id": artifact_id,
    "name": "code",
    "description": "test code",
    "timestamp": "2023-07-17T19:11:43",
    "file_names": ["code.py"],
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
mock_code = Mock()
mock_code.content = open("tests/test_code_to_amr/code.py").read().encode()
mock_code.status_code = 200

mock_ta1_response = Mock()
amr = json.loads(open("tests/test_code_to_amr/amr.json").read())
mock_ta1_response.json.return_value = amr
mock_ta1_response.text = json.dumps(amr)
mock_ta1_response.status_code = 200

# Note: this mock response is used for both POSTs
# made by TDS including a POST to /models and to /model_configurations
model_id = 123
mock_tds_response = Mock()
tds_response = {"id": model_id}
mock_tds_response.json.return_value = tds_response
mock_tds_response.status_code = 200

# Mock the TDS artifact
mock_updated_tds_artifact = Mock()
artifact = {
    "id": artifact_id,
    "name": "code",
    "description": "test code",
    "timestamp": "2023-07-17T19:11:43",
    "file_names": ["code.py"],
    "metadata": {"model_id": model_id},
}
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
    live = os.environ.get("LIVE", "FALSE")
    if "tds" in url:
        print("Mocking response from TDS")
        return mock_tds_response
    if "ta1" in url:
        print("Mocking response from TA1")
        return mock_ta1_response
    elif live == "TRUE":
        print("Sending request to LIVE TA1 Service")
        return original_post(*args, **kwargs)  # Call the original


#######################################
############## Run Tests ##############
#######################################


# Note that the patches have to be in reverse order of the
# test function arguments
@patch("requests.put")  # patch anytime a PUT is made
@patch("requests.get")  # patch anytime a GET is made
@patch(
    "requests.post", side_effect=decide_post_response
)  # patch anytime a POST is made
@patch("api.utils.get_queue", return_value=queue)  # mock the redis queue
def test_code_to_amr(mock_queue, mock_post, mock_get, mock_put):
    # response from TDS for artifact
    # response from TDS for presigned URL
    # response from S3 to pull down the code file
    mock_get.side_effect = [mock_tds_artifact, mock_presigned_download_url, mock_code]

    # response from TDS after updateing artifact
    mock_put.side_effect = [mock_updated_tds_artifact]

    # Define the query parameters
    query_params = {
        "artifact_id": artifact_id,
        "name": "test model",
        "description": "test description",
    }

    # Call the endpoint
    response = client.post(
        "/code_to_amr",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()
    print(results)

    # Assert the status code and response
    assert response.status_code == 200
    assert results.get("status") == "finished"
    assert results.get("job_error") == None

    # TODO: in case of LIVE situation, don't test the exact response `amr`
    # TODO: instead test that the result amr is schema compliant
    assert results.get("result", {}).get("job_result") == {
        "status_code": 200,
        "amr": amr,
        "tds_model_id": tds_response.get("id"),
        "tds_configuration_id": tds_response.get("id"),
        "error": None,
    }
