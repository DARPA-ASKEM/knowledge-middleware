import json
import os
import requests

import pytest
import logging

from lib.settings import settings

logger = logging.getLogger(__name__)

@pytest.mark.resource("basic_pdf_extraction")
def test_pdf_extractions(context_dir, http_mock, client, worker, tds_artifact, file_storage):
    #### ARRANGE ####
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"
    tds_artifact["file_names"] = ["paper.pdf"]
    tds_artifact["metadata"] = {"text": text}
    file_storage.upload("paper.pdf", "TEST TEXT")

    extractions = json.load(open(f"{context_dir}/extractions.json"))
    http_mock.post(f"{settings.TA1_UNIFIED_URL}/text-reading/integrated-text-extractions?annotate_skema=True&annotate_mit=True", json=extractions)

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
    status_response = client.get(f"/status/{job_id}")

    #### ASSERT ####
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert status_response.json().get("status") == "finished"


@pytest.mark.resource("basic_pdf_to_text")
def test_pdf_to_text(context_dir, http_mock, client, worker, tds_artifact, file_storage):
    #### ARRANGE ####
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"
    tds_artifact["file_names"] = ["paper.pdf"]
    file_storage.upload("paper.pdf", "TEST TEXT")

    query_params = {
        "artifact_id": tds_artifact["id"],
    }

    extractions = json.load(open(f"{context_dir}/text.json"))
    http_mock.post(f"{settings.TA1_UNIFIED_URL}/text-reading/cosmos_to_json", json=extractions)
    
    #### ACT ####
    response = client.post(
        "/pdf_to_text",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()
    job_id = results.get("id")
    worker.work(burst=True)
    status_response = client.get(f"/status/{job_id}")

    #### ASSERT ####
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert status_response.json().get("status") == "finished"


@pytest.mark.resource("basic_code_to_amr")
def test_code_to_amr(context_dir, http_mock, client, worker, tds_artifact, file_storage):
    #### ARRANGE ####
    code = open(f"{context_dir}/code.py").read()
    tds_artifact["file_names"] = ["code.py"]
    file_storage.upload("code.py", code)

    query_params = {
        "artifact_id": tds_artifact["id"],
        "name": "test model",
        "description": "test description",
    }

    amr = json.load(open(f"{context_dir}/amr.json"))
    http_mock.post(f"{settings.TA1_UNIFIED_URL}/workflows/code/snippets-to-pn-amr", json=amr)
    http_mock.post(f"{settings.TDS_URL}/models", json={"id": "test"})
    http_mock.post(f"{settings.TDS_URL}/model_configurations", json={"id": "test"})
    
    #### ACT ####
    response = client.post(
        "/code_to_amr",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()
    job_id = results.get("id")
    worker.work(burst=True)
    status_response = client.get(f"/status/{job_id}")

    #### ASSERT ####
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert status_response.json().get("status") == "finished"
