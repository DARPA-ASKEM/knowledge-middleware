import json
from unittest.mock import Mock, patch
import os
import requests
import sys

import logging

logger = logging.getLogger(__name__)

from tests.test_utils import AMR

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

char_limit = 250

# Mock the TDS document/paper artifact
text_json = json.loads(open("tests/test_pdf_extractions/text.json").read())
text = ""
for d in text_json:
    text += f"{d['content']}\n"

mock_tds_artifact = Mock()
artifact_id = "artifact-paper-123"
artifact = {
    "id": artifact_id,
    "name": "paper",
    "description": "test paper",
    "timestamp": "2023-07-17T19:11:43",
    "file_names": ["paper.pdf"],
    "metadata": {"text": text[:char_limit]},
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

# Mock the TDS dataset artifact
mock_tds_dataset = Mock()
dataset_id = "artifact-dataset-123"
dataset = {
    "id": dataset_id,
    "name": "data",
    "description": "test data",
    "timestamp": "2023-07-17T19:11:43",
    "file_names": ["data.csv"],
    "metadata": {},
}
mock_tds_dataset.json.return_value = dataset
mock_tds_dataset.text = json.dumps(dataset)
mock_tds_dataset.status_code = 200

# Mock the downloaded data
mock_data = Mock()
mock_data.content = open("tests/test_profile_dataset/data.csv").read().encode()
mock_data.status_code = 200

# Mock the downloaded code
mock_paper = Mock()
mock_paper.content = "some encoded PDF content goes here".encode()
mock_paper.status_code = 200

mock_ta1_response = Mock()
data_card = json.loads(open("tests/test_profile_dataset/data_card.json").read())
mock_ta1_response.json.return_value = data_card
mock_ta1_response.text = json.dumps(data_card)
mock_ta1_response.status_code = 200

# Mock the updated TDS dataset artifact
mock_tds_dataset_update_put = Mock()
tds_response = {"id": dataset_id}
mock_tds_dataset_update_put.json.return_value = tds_response
mock_tds_dataset_update_put.text = json.dumps(tds_response)
mock_tds_dataset_update_put.status_code = 200


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
    if "mit" in url and live == "FALSE":
        logger.info("Mocking response from TA1")
        return mock_ta1_response
    elif live == "TRUE":
        logger.info("Sending request to LIVE TA1 Service")
        return original_post(*args, **kwargs)  # Call the original


#######################################
############## Run Tests ##############
#######################################


# Note that the patches have to be in reverse order of the
# test function arguments
@patch("requests.get")  # patch anytime a GET is made
@patch("requests.put")  # patch anytime a PUT is made
@patch(
    "requests.post", side_effect=decide_post_response
)  # patch anytime a POST is made
@patch("api.utils.get_queue", return_value=queue)  # mock the redis queue
def test_profile_dataset(mock_queue, mock_post, mock_put, mock_get):
    logging.info(
        f"Testing with {char_limit} set on the document submission to avoid context overruns with the LLM"
    )

    mock_get.side_effect = [
        mock_tds_artifact,
        mock_presigned_download_url,
        mock_paper,
        mock_tds_dataset,
        mock_presigned_download_url,
        mock_data,
    ]

    # response from TDS after updating artifact
    mock_put.side_effect = [mock_tds_dataset_update_put]

    # Define the query parameters
    query_params = {"artifact_id": artifact_id}

    # Call the endpoint
    response = client.post("/profile_dataset/{dataset_id}", params=query_params)
    results = response.json()

    # Assert the status code and response
    assert response.status_code == 200
    assert results.get("status") == "finished", results.get("result", {}).get(
        "job_error"
    )
    assert results.get("result", {}).get("job_error") == None
    assert (
        results.get("result", {}).get("job_result", {}).get("message", None)
        == "Data card generated and updated in TDS"
    )
