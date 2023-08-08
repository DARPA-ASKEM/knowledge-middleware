import json
from unittest.mock import Mock, patch
import requests
import os
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

mock_ta1_response = Mock()
amr = json.loads(open("tests/test_equations_to_amr/amr.json").read())
mock_ta1_response.json.return_value = amr
mock_ta1_response.text = json.dumps(amr)
mock_ta1_response.status_code = 200

# Note: this mock response is used for both POSTs
# made by TDS including a POST to /models and to /model_configurations
mock_tds_response = Mock()
tds_response = {"id": "123"}
mock_tds_response.json.return_value = tds_response
mock_tds_response.status_code = 200

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
    if "tds" in url:
        logger.info("Mocking response from TDS")
        return mock_tds_response
    if "ta1" in url:
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
@patch(
    "requests.post", side_effect=decide_post_response
)  # patch anytime a POST is made
@patch("api.utils.get_queue", return_value=queue)  # mock the redis queue
def test_equations_to_amr(mock_queue, mock_post):
    # The endpoint parameters
    payload = open("tests/test_equations_to_amr/equations.txt").read()

    # Define the query parameters
    query_params = {
        "equation_type": "latex",
        "model": "petrinet",
        "name": "test model",
        "description": "test description",
    }

    # Call the endpoint
    response = client.post(
        "/equations_to_amr",
        params=query_params,
        data=payload,
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
            "status_code": 200,
            "amr": amr,
            "tds_model_id": tds_response.get("id"),
            "tds_configuration_id": tds_response.get("id"),
            "error": None,
        }

    # If testing live, we focus on validating the AMR against its provided JSON Schema
    elif live == "TRUE":
        result_amr = results.get("result", {}).get("job_result", {}).get("amr", None)
        amr_instance = AMR(result_amr)
        assert (
            amr_instance.is_valid()
        ), f"AMR failed to validate to its provided schema: {amr_instance.get_validation_error()}"
