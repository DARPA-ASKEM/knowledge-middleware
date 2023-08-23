import json
import os
import requests

import pytest
import logging

logger = logging.getLogger(__name__)

@pytest.mark.resource("basic_pdf_extraction")
def test_pdf_extractions(client, worker, tds, file_storage):

    artifact_id = "artifact-123" #DELETE
    
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
    assert results.get("status") == "queued"
    job_id = results.get("id")

    worker.work(burst=True)

    response = client.post(
        "/pdf_extractions",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    
    status_response = client.get(f"/status/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json().get("status") == "finished"
