import json
import os
import sys
from datetime import datetime
from unittest.mock import Mock, PropertyMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "workers"))

# Create a test application
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)

# Create a fake redis server and a fake redis instance
from fakeredis import FakeStrictRedis
from rq import Queue

# Create a fake redis server and a fake redis instance
queue = Queue(is_async=False, connection=FakeStrictRedis())


@patch("workers.utils.equation_to_amr_call")  # mock actual call to TA1
@patch("workers.utils.put_amr_to_tds")  # mock put to TDS after retrieval of AMR
@patch("api.utils.get_queue", return_value=queue)  # mock the redis queue
def test_equations_to_amr(mock_ta1_response, mock_tds_response, mock_queue):
    # The mock responses
    amr = json.loads(open("tests/data/test_1_equations_to_amr/amr.json").read())
    mock_ta1_response.json.return_value = amr
    mock_ta1_response.text = json.dumps(amr)
    mock_ta1_response.status_code = 200

    tds_response = {"model_id": "123", "configuration_id": "456"}
    mock_tds_response = Mock()
    mock_tds_response.return_value = tds_response
    mock_tds_response.status_code = 200

    # The endpoint parameters
    payload = open("tests/data/test_1_equations_to_amr/equations.txt").read()

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

    print(response.json())

    # Assert the status code and response
    assert response.status_code == 200
    assert response.json() == {
        "status_code": 200,
        "amr": amr,
        "tds_model_id": tds_response.get("model_id"),
        "tds_configuration_id": tds_response.get("configuration_id"),
        "error": None,
    }
