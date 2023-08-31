import json
import os
import logging
from shutil import rmtree

import pytest
import requests
from rq.job import Job

from lib.settings import settings
from tests.utils import get_parameterizations, record_quality_check, AMR

logger = logging.getLogger(__name__)

params = get_parameterizations()
if os.path.exists("tests/output"): rmtree("tests/output")


@pytest.mark.parametrize("resource", params["pdf_extraction"])
def test_pdf_extraction(context_dir, http_mock, client, worker, gen_tds_artifact, file_storage):
    #### ARRANGE ####
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"
    tds_artifact = gen_tds_artifact()
    tds_artifact["file_names"] = ["paper.pdf"]
    tds_artifact["metadata"] = {"text": text}
    file_storage.upload("paper.pdf", "TEST TEXT")

    if settings.MOCK_TA1:
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


@pytest.mark.parametrize("resource", params["pdf_to_text"])
def test_pdf_to_text(context_dir, http_mock, client, worker, gen_tds_artifact, file_storage):
    #### ARRANGE ####
    tds_artifact = gen_tds_artifact()
    tds_artifact["file_names"] = ["paper.pdf"]
    file_storage.upload("paper.pdf", "TEST TEXT")

    query_params = {
        "artifact_id": tds_artifact["id"],
    }

    if settings.MOCK_TA1:
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


@pytest.mark.parametrize("resource", params["code_to_amr"])
def test_code_to_amr(context_dir, http_mock, client, worker, gen_tds_artifact, file_storage):
    #### ARRANGE ####
    code = open(f"{context_dir}/code.py").read()
    tds_code = gen_tds_artifact(code=True)
    tds_code["file_names"] = ["code.py"]
    file_storage.upload("code.py", code)

    query_params = {
        "code_id": tds_code["id"],
        "name": "test model",
        "description": "test description",
    }

    http_mock.post(f"{settings.TDS_URL}/provenance", json={})
    http_mock.post(f"{settings.TDS_URL}/models", json={"id": "test"})
    http_mock.post(f"{settings.TDS_URL}/model_configurations", json={"id": "test"})
    if settings.MOCK_TA1:
        amr = json.load(open(f"{context_dir}/amr.json"))
        http_mock.post(f"{settings.TA1_UNIFIED_URL}/workflows/code/snippets-to-pn-amr", json=amr)
    
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

    job = Job.fetch(job_id, connection=worker.connection)
    amr_instance = AMR(job.result["amr"])

    #### ASSERT ####
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert status_response.json().get("status") == "finished"

    assert (
             amr_instance.is_valid()
    ), f"AMR failed to validate to its provided schema: {amr_instance.validation_error}"

    #### POSTAMBLE ####
    record_quality_check(context_dir, "code_to_amr", "F1 Score", amr_instance.f1(amr))
    record_quality_check(context_dir, "code_to_amr", "Estimated Time of Completion", 0)
    

@pytest.mark.parametrize("resource", params["equations_to_amr"])
def test_equations_to_amr(context_dir, http_mock, client, worker, file_storage):
    #### ARRANGE ####
    equations = open(f"{context_dir}/equations.txt").read()

    query_params = {
        "equation_type": "latex",
        "model": "petrinet",
        "name": "test model",
        "description": "test description",
    }


    amr = json.load(open(f"{context_dir}/amr.json"))
    http_mock.post(f"{settings.TDS_URL}/models", json={"id": "test"})
    http_mock.post(f"{settings.TDS_URL}/model_configurations", json={"id": "test"})
    if settings.MOCK_TA1:
        http_mock.post(f"{settings.TA1_UNIFIED_URL}/workflows/latex/equations-to-amr", json=amr)
    
    #### ACT ####
    response = client.post(
        "/equations_to_amr",
        params=query_params,
        data=equations,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()
    job_id = results.get("id")
    worker.work(burst=True)
    status_response = client.get(f"/status/{job_id}")
    
    job = Job.fetch(job_id, connection=worker.connection)
    amr_instance = AMR(job.result["amr"])

    #### ASSERT ####
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert status_response.json().get("status") == "finished"

    assert (
             amr_instance.is_valid()
    ), f"AMR failed to validate to its provided schema: {amr_instance.validation_error}"

    #### POSTAMBLE ####
    record_quality_check(context_dir, "equations_to_amr", "F1 Score", amr_instance.f1(amr))
    record_quality_check(context_dir, "code_to_amr", "Estimated Time of Completion", 0)


@pytest.mark.parametrize("resource", params["profile_dataset"])
def test_profile_dataset(context_dir, http_mock, client, worker, gen_tds_artifact, file_storage):
    #### ARRANGE ####
    CHAR_LIMIT = 250
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"
    tds_artifact = gen_tds_artifact()
    tds_artifact["file_names"] = ["paper.pdf"]
    tds_artifact["metadata"] = {"text": text[:CHAR_LIMIT]}
    query_params = {
        "artifact_id": tds_artifact["id"],
    }
    csvfile = open(f"{context_dir}/data.csv").read()
    file_storage.upload("paper.pdf", "TEST TEXT")
    file_storage.upload("data.csv", csvfile)

    
    dataset = {
        "id": tds_artifact["id"],
        "name": "data",
        "description": "test data",
        "timestamp": "2023-07-17T19:11:43",
        "file_names": ["data.csv"],
        "metadata": {},
    }
    http_mock.get(f"{settings.TDS_URL}/datasets/{dataset['id']}", json=dataset)
    http_mock.put(f"{settings.TDS_URL}/datasets/{dataset['id']}", json={"id": dataset["id"]})
    if settings.MOCK_TA1:
        data_card = json.load(open(f"{context_dir}/data_card.json"))
        http_mock.post(f"{settings.MIT_TR_URL}/cards/get_data_card", json=data_card)

    #### ACT ####
    response = client.post(
        f"/profile_dataset/{tds_artifact['id']}",
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

    
@pytest.mark.parametrize("resource", params["profile_model"])
def test_profile_model(context_dir, http_mock, client, worker, gen_tds_artifact, file_storage):
    #### ARRANGE ####
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"
    text_artifact = gen_tds_artifact()
    text_artifact["file_names"] = ["paper.pdf"]
    text_artifact["metadata"] = {"text": text}
    file_storage.upload("paper.pdf", "TEST TEXT")

    code = open(f"{context_dir}/code.py").read()
    code_artifact = gen_tds_artifact()
    code_artifact["file_names"] = ["code.py"]
    file_storage.upload("code.py", code)
    
    amr = json.load(open(f"{context_dir}/amr.json"))
    http_mock.post(f"{settings.TDS_URL}/provenance/search?search_type=models_from_code", json={"result": [text_artifact["id"]]})
    http_mock.get(f"{settings.TDS_URL}/models/{text_artifact['id']}", json={"id":text_artifact["id"], "model": amr})
    http_mock.put(f"{settings.TDS_URL}/models/{text_artifact['id']}", json={"id": text_artifact["id"]})
    if settings.MOCK_TA1:
        model_card = json.load(open(f"{context_dir}/model_card.json"))
        http_mock.post(f"{settings.MIT_TR_URL}/cards/get_model_card", json=model_card)

    query_params = {"paper_artifact_id": text_artifact["id"]}

    #### ACT ####
    response = client.post(
        f"/profile_model/{text_artifact['id']}",
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
