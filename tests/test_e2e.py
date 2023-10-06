import json
import os
import logging

import pytest
import requests
from rq.job import Job

from lib.settings import settings, ExtractionServices
from tests.utils import get_parameterizations, record_quality_check, AMR

logger = logging.getLogger(__name__)

params = get_parameterizations()


@pytest.mark.parametrize("resource", params["pdf_extraction"])
def test_pdf_extraction(
    context_dir, http_mock, client, worker, gen_tds_artifact, file_storage, resource
):
    #### ARRANGE ####
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"
    tds_artifact = gen_tds_artifact(
        id=f"test_pdf_extractions_{resource}",
        file_names=["paper.pdf"],
        text=text,
    )
    pdf = open(f"{context_dir}/paper.pdf", "rb")
    file_storage.upload("paper.pdf", pdf)
    document_id = tds_artifact["id"]

    if settings.MOCK_TA1:
        extractions = json.load(open(f"{context_dir}/extractions.json"))
        http_mock.post(
            f"{settings.TA1_UNIFIED_URL}/text-reading/integrated-text-extractions?annotate_skema=True&annotate_mit=True",
            json=extractions,
        )

    query_params = {
        "document_id": document_id,
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
    assert (
        status_response.json().get("status") == "finished"
    ), f"The RQ job failed.\n{job.latest_result().exc_string}"

    #### POSTAMBLE ####
    scenario = context_dir.split("/")[-1]
    if not settings.MOCK_TA1 and "sidarthe" in context_dir:
        # Can only quality check for SIDARTHE
        logger.debug(f"Evaluating PDF extractions from SKEMA")
        eval = requests.get(
            f"{settings.TA1_UNIFIED_URL}/text-reading/eval"
        )
        logger.info(f"PDF extraction evaluation result: {eval.text}")
        if eval.status_code < 300:
            accuracy = json.dumps(eval.json())
        else:
            accuracy = False
        record_quality_check(context_dir, "profile_model", "Accuracy", accuracy)




@pytest.mark.parametrize("resource", params["pdf_to_cosmos"])
def test_pdf_to_cosmos(
    context_dir, http_mock, client, worker, gen_tds_artifact, file_storage, resource
):
    #### ARRANGE ####
    tds_artifact = gen_tds_artifact(
        id=f"test_pdf_to_cosmos_{resource}", file_names=["paper.pdf"]
    )
    pdf_file = open(f"{context_dir}/paper.pdf", "rb")
    file_storage.upload("paper.pdf", pdf_file)
    query_params = {
        "document_id": tds_artifact["id"],
    }

    if settings.MOCK_TA1:
        print(settings.PDF_EXTRACTOR)
        if settings.PDF_EXTRACTOR == ExtractionServices.SKEMA:
            extractions = json.load(open(f"{context_dir}/text.json"))
            http_mock.post(
                f"{settings.TA1_UNIFIED_URL}/text-reading/cosmos_to_json", json=extractions
            )
        elif settings.PDF_EXTRACTOR == ExtractionServices.COSMOS:        
            job_id = 'test-job'
            text_extractions_result = json.load(open(f"{context_dir}/cosmos_result.json"))
            equations = json.load(open(f"{context_dir}/cosmos_equations.json"))
            figures = json.load(open(f"{context_dir}/cosmos_figures.json"))
            tables = json.load(open(f"{context_dir}/cosmos_tables.json"))
            with open(f"{context_dir}/paper_cosmos_output.zip", 'rb') as f:
                zip_content = f.read()

            cosmos_job_response = {'job_id': job_id, 
                                    'status_endpoint': f"{settings.COSMOS_URL}/process/{job_id}/status",
                                    'result_endpoint': f"{settings.COSMOS_URL}/process/{job_id}/result"}
            
            cosmos_job_status = {'job_started': True, 'job_completed': True, 'error': None}
            
            http_mock.post(
                f"{settings.COSMOS_URL}/process/", json=cosmos_job_response
            )
            http_mock.get(
                f"{settings.COSMOS_URL}/process/{job_id}/status", json=cosmos_job_status
            )            
            http_mock.get(
                f"{settings.COSMOS_URL}/process/{job_id}/result", content=zip_content
            )
            http_mock.get(
                f"{settings.COSMOS_URL}/process/{job_id}/result/text", json=text_extractions_result
            )
            http_mock.get(
                f"{settings.COSMOS_URL}/process/{job_id}/result/extractions/equations", json=equations
            )
            http_mock.get(
                f"{settings.COSMOS_URL}/process/{job_id}/result/extractions/figures", json=figures
            )      
            http_mock.get(
                f"{settings.COSMOS_URL}/process/{job_id}/result/extractions/tables", json=tables
            )                                    

    #### ACT ####
    response = client.post(
        "/pdf_to_cosmos",
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
    assert (
        status_response.json().get("status") == "finished"
    ), f"The RQ job failed.\n{job.latest_result().exc_string}"


@pytest.mark.parametrize("resource", params["code_to_amr"])
def test_code_to_amr(
    context_dir, http_mock, client, worker, gen_tds_artifact, file_storage, resource
):
    #### ARRANGE ####
    code = open(f"{context_dir}/code.py").read()
    tds_code = gen_tds_artifact(
        code=True, id=f"test_code_to_amr_{resource}", file_names=["code.py"]
    )
    tds_code["file_names"] = ["code.py"]
    file_storage.upload("code.py", code)

    query_params = {
        "code_id": tds_code["id"],
        "name": "test model",
        "description": "test description",
    }

    if settings.MOCK_TDS:
        http_mock.post(f"{settings.TDS_URL}/provenance", json={})
        http_mock.post(f"{settings.TDS_URL}/models", json={"id": "test"})
        http_mock.post(f"{settings.TDS_URL}/model_configurations", json={"id": "test"})
    if settings.MOCK_TA1:
        amr = json.load(open(f"{context_dir}/amr.json"))
        http_mock.post(
            f"{settings.TA1_UNIFIED_URL}/workflows/code/snippets-to-pn-amr", json=amr
        )
    elif os.path.exists(f"{context_dir}/amr.json"):
        amr = json.load(open(f"{context_dir}/amr.json"))

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
    if job.result is not None:
        amr_instance = AMR(job.result["amr"])

    #### ASSERT ####
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert (
        status_response.json().get("status") == "finished"
    ), f"The RQ job failed.\n{job.latest_result().exc_string}"

    assert (
        amr_instance.is_valid()
    ), f"AMR failed to validate to its provided schema: {amr_instance.validation_error}"

    #### POSTAMBLE ####
    # if 'amr' in locals():
    #     record_quality_check(context_dir, "code_to_amr", "F1 Score", amr_instance.f1(amr))


@pytest.mark.parametrize("resource", params["equations_to_amr"])
def test_equations_to_amr(context_dir, http_mock, client, worker, file_storage):
    #### ARRANGE ####

    # Function to store written model configurations for later assertions.
    storage = []

    def write_to_fake_configs(req, resp):
        json_body = json.loads(req._request.body)
        storage.append(json_body)
        return {"id": "configuration_test_id"}

    equations = open(f"{context_dir}/equations.txt").read()

    query_params = {
        "equation_type": "latex",
        "model": "petrinet",
        "name": "test model",
        "description": "test description",
    }

    query_params_config_test = {
        "equation_type": "latex",
        "model": "petrinet",
        "model_id": "test2",
        "name": "test model 2",
        "description": "test description 2",
    }
   
    mock_amr_header = {
            "name": "Test Existing SIR Model",
            "description": "Test Existing SIR model"
        }

    if settings.MOCK_TDS:
        http_mock.post(f"{settings.TDS_URL}/models", json={"id": "test"})
        http_mock.get(f"{settings.TDS_URL}/models/test2", json={"header": mock_amr_header})
        http_mock.put(f"{settings.TDS_URL}/models/test2", json={"id": "test2"})
        http_mock.post(
            f"{settings.TDS_URL}/model_configurations", json=write_to_fake_configs
        )
    if settings.MOCK_TA1:
        amr = json.load(open(f"{context_dir}/amr.json"))
        http_mock.post(
            f"{settings.TA1_UNIFIED_URL}/workflows/latex/equations-to-amr", json=amr
        )
    elif os.path.exists(f"{context_dir}/amr.json"):
        amr = json.load(open(f"{context_dir}/amr.json"))

    #### ACT ####
    # Case 1
    response = client.post(
        "/equations_to_amr",
        params=query_params,
        data=equations,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()
    logger.info("ENDPOINT RESPONSE")
    logger.info(response.text)
    job_id = results.get("id")
    worker.work(burst=True)
    status_response = client.get(f"/status/{job_id}")

    job = Job.fetch(job_id, connection=worker.connection)
    if job.result is not None:
        amr_instance = AMR(job.result["amr"])

    # Case 2
    # Tests the equation to AMR with a predefined model_id.
    config_response = client.post(
        "/equations_to_amr",
        params=query_params_config_test,
        data=equations,
        headers={"Content-Type": "application/json"},
    )
    logger.info(f"CONFIG RESP: {config_response}")
    results_config_test = config_response.json()
    job_id_config = results_config_test.get("id")
    status_config_response = client.get(f"/status/{job_id_config}")

    job_id = results_config_test.get("id")
    worker.work(burst=True)
    status_response = client.get(f"/status/{job_id}")

    job2 = Job.fetch(job_id, connection=worker.connection)
    if job2.result is not None:
        amr_instance_2 = AMR(job2.result["amr"])    

    #### ASSERT ####
    # Case 1
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert (
        status_response.json().get("status") == "finished"
    ), f"The RQ job failed.\n{job.latest_result().exc_string}"

    assert (
        amr_instance.is_valid()
    ), f"AMR failed to validate to its provided schema: {amr_instance.validation_error}"

    assert len(storage) >= 1
    assert storage[0].get("model_id") == "test"

    # Case 2
    # Assertions for predefined model id case.
    assert results_config_test.get("status") == "queued"
    assert status_config_response.status_code == 200

    assert storage[1].get("model_id") == "test2"
    assert amr_instance_2.header["name"] == mock_amr_header["name"]

    #### POSTAMBLE ####
    # if 'amr' in locals():
    #     record_quality_check(context_dir, "equations_to_amr", "F1 Score", amr_instance.f1(amr))


@pytest.mark.parametrize("resource", params["profile_dataset"])
def test_profile_dataset(
    context_dir, http_mock, client, worker, gen_tds_artifact, file_storage, resource
):
    #### ARRANGE ####
    CHAR_LIMIT = 250
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"
    tds_artifact = gen_tds_artifact(
        id=f"test_profile_dataset_{resource}",
        file_names=["paper.pdf"],
        metadata={"text": text[:CHAR_LIMIT]},
    )
    query_params = {
        "artifact_id": tds_artifact["id"],
    }
    pdf = open(f"{context_dir}/paper.pdf", "rb")
    file_storage.upload("paper.pdf", pdf)
    csvfile = open(f"{context_dir}/data.csv").read()
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
    http_mock.put(
        f"{settings.TDS_URL}/datasets/{dataset['id']}", json={"id": dataset["id"]}
    )
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
    assert (
        status_response.json().get("status") == "finished"
    ), f"The RQ job failed.\n{job.latest_result().exc_string}"


@pytest.mark.parametrize("resource", params["profile_model"])
def test_profile_model(
    context_dir, http_mock, client, worker, gen_tds_artifact, file_storage, resource
):
    #### ARRANGE ####
    text_json = json.load(open(f"{context_dir}/text.json"))
    text = ""
    for d in text_json:
        text += f"{d['content']}\n"
    document = gen_tds_artifact(
        id=f"test_profile_model_document_{resource}",
        file_names=["paper.pdf"],
        metadata={},
        text=text,
    )
    pdf = open(f"{context_dir}/paper.pdf", "rb")
    file_storage.upload("paper.pdf", pdf)

    code = open(f"{context_dir}/code.py").read()
    code_artifact = gen_tds_artifact(
        id=f"test_profile_model_code_{resource}", code=True, file_names=["code.py"]
    )
    file_storage.upload("code.py", code)

    model_id = "test_profile_model"
    amr = json.load(open(f"./tests/amr.json"))
    if settings.MOCK_TDS:
        http_mock.post(
            f"{settings.TDS_URL}/provenance/search?search_type=models_from_code",
            json={"result": [code_artifact["id"]]},
        )
        http_mock.get(
            f"{settings.TDS_URL}/models/{model_id}", json={"id": model_id, "model": amr}
        )
        http_mock.put(f"{settings.TDS_URL}/models/{model_id}", json={"id": model_id})
    else:
        amr["id"] = model_id
        requests.post(f"{settings.TDS_URL}/models", json=amr)
        requests.post(
            f"{settings.TDS_URL}/provenance",
            json={
                "timestamp": "2023-09-05T17:41:18.187841",
                "relation_type": "EXTRACTED_FROM",
                "left": model_id,
                "left_type": "Model",
                "right": code_artifact["id"],
                "right_type": "Code",
            },
        )

    if settings.MOCK_TA1:
        model_card = json.load(open(f"{context_dir}/model_card.json"))
        http_mock.post(f"{settings.MIT_TR_URL}/cards/get_model_card", json=model_card)

    query_params = {
        "document_id": document["id"],
        "": "",
    }

    #### ACT ####
    response = client.post(
        f"/profile_model/{model_id}",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()
    job_id = results.get("id")
    worker.work(burst=True)
    status_response = client.get(f"/status/{job_id}")
    generated_card = status_response.json()["result"]["job_result"]["card"]

    #### ASSERT ####
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert (
        status_response.json().get("status") == "finished"
    ), f"The RQ job failed.\n{job.latest_result().exc_string}"
    #### POSTAMBLE ####
    if not settings.MOCK_TA1 and os.path.exists(f"{context_dir}/ground_truth_model_card.json"):
        logger.debug(f"Evaluating model card: {generated_card}")
        files = {
            "test_json_file": json.dumps(generated_card),
            "ground_truth_file": open(f"{context_dir}/ground_truth_model_card.json")
        }    
        eval = requests.post(
            f"{settings.MIT_TR_URL}/evaluation/eval_model_card", 
            params={"gpt_key": settings.OPENAI_API_KEY},
            files=files
        )
        logger.info(f"Model profiling evaluation result: {eval.text}")
        if eval.status_code < 300:
            accuracy = eval.json()["accuracy"]
        else:
            accuracy = False
        record_quality_check(context_dir, "profile_model", "Accuracy", accuracy)


@pytest.mark.parametrize("resource", params["link_amr"])
def test_link_amr(
    context_dir, http_mock, client, worker, gen_tds_artifact, gen_tds_model, file_storage, resource
):
    #### ARRANGE ####
    extractions = json.load(open(f"{context_dir}/extractions.json"))
    amr = json.load(open(f"{context_dir}/amr.json"))
    model_id = "test_model"
    document_id = f"test_link_amr_document_{resource}"

    # TODO: if TDS is NOT mocked, how do we know the ID of the document
    # that is generated?
    document = gen_tds_artifact(
        id=document_id,
        file_names=["paper.pdf"],
        metadata=extractions
    )
    
    pdf = open(f"{context_dir}/paper.pdf", "rb")
    file_storage.upload("paper.pdf", pdf)

    # overwrite model_id with the response in case TDS is NOT mocked and we get
    # back a real model ID
    model_id = gen_tds_model(model_id=model_id, amr=amr)    

    if settings.MOCK_TDS:
        http_mock.get(
            f"{settings.TDS_URL}/models/{model_id}", json=amr
        )
        http_mock.get(
            f"{settings.TDS_URL}/documents/{document_id}", json=document
        )        
        http_mock.put(f"{settings.TDS_URL}/models/{model_id}", json={"id": model_id})

    if settings.MOCK_TA1:
        http_mock.post(
            f"{settings.TA1_UNIFIED_URL}/metal/link_amr",
            json=amr,
        )

    query_params = {
        "model_id": model_id,
        "document_id": document_id
    }

    #### ACT ####
    response = client.post(
        "/link_amr",
        params=query_params,
        headers={"Content-Type": "application/json"},
    )
    results = response.json()
    job_id = results.get("id")
    worker.work(burst=True)
    status_response = client.get(f"/status/{job_id}")

    job = Job.fetch(job_id, connection=worker.connection)

    if job.result is not None:
        amr_instance = AMR(job.result["amr"])

    #### ASSERT ####
    assert results.get("status") == "queued"
    assert status_response.status_code == 200
    assert (
        status_response.json().get("status") == "finished"
    ), f"The RQ job failed.\n{job.latest_result().exc_string}"

    assert (
        amr_instance.is_valid()
    )