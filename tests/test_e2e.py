import json
import os
import requests

import pytest
import logging

logger = logging.getLogger(__name__)

@pytest.mark.resource("basic_pdf_extraction")
def test_pdf_extractions(context_dir, client, worker, tds_artifact, file_storage):
    #### ARRANGE ####
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"
    tds_artifact["file_names"] = ["paper.pdf"]
    tds_artifact["metadata"] = {"text": text}
    file_storage.upload("paper.pdf", "TEST TEXT")

    query_params = {
        "artifact_id": tds_artifact["id"],
        "annotate_skema": True,
        "annotate_mit": True,
        "name": None,
        "description": None,
    }

    #### ACT ####
    response = client.post(
        "/pdf_extractions",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()
    job_id = results.get("id")
    worker.work(burst=True)
    response = client.post(
        "/pdf_extractions",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    status_response = client.get(f"/status/{job_id}")

    #### ASSERT ####
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert status_response.json().get("status") == "finished"
