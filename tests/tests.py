from unittest.mock import patch

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_equations_to_amr():
    # Define the mock responses
    mock_rq_job_response = {"job": "success"}
    mock_service_response = {"service": "success"}

    with patch(
        "my_project.my_module.rq_function", return_value=mock_rq_job_response
    ), patch("my_project.my_module.requests.post", return_value=mock_service_response):
        # Call the endpoint
        response = client.post("/equations_to_amr", json={"key": "value"})

        # Check the response
        assert response.status_code == 200
        assert response.json() == {"job": "success", "service": "success"}
