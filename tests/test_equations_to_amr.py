import json
from unittest.mock import Mock, patch
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "workers"))

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
@patch("requests.post")  # patch anytime a POST is made
@patch("api.utils.get_queue", return_value=queue)  # mock the redis queue
def test_equations_to_amr(mock_queue, mock_post):
    # The mock responses
    mock_ta1_response = Mock()
    amr = json.loads(open("tests/data/test_equations_to_amr/amr.json").read())
    mock_ta1_response.json.return_value = amr
    mock_ta1_response.text = json.dumps(amr)
    mock_ta1_response.status_code = 200

    # Note: this mock response is used for both POSTs
    # made by TDS including a POST to /models and to /model_configurations
    mock_tds_response = Mock()
    tds_response = {"id": "123"}
    mock_tds_response.json.return_value = tds_response
    mock_tds_response.status_code = 200

    mock_post.side_effect = [mock_ta1_response, mock_tds_response, mock_tds_response]

    # The endpoint parameters
    payload = open("tests/data/test_equations_to_amr/equations.txt").read()

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
    assert results.get("status") == "finished"
    assert results.get("job_error") == None
    assert results.get("result", {}).get("job_result") == {
        "status_code": 200,
        "amr": amr,
        "tds_model_id": tds_response.get("id"),
        "tds_configuration_id": tds_response.get("id"),
        "error": None,
    }
