import io
import json
import os
import urllib
import sys
import requests
import pandas

from utils import (
    put_amr_to_tds,
    put_artifact_extraction_to_tds,
    get_artifact_from_tds,
    get_dataset_from_tds,
)

TDS_API = os.getenv("TDS_URL")
SKEMA_API = os.getenv("SKEMA_RS_URL")
UNIFIED_API = os.getenv("TA1_UNIFIED_URL")
MIT_API = os.getenv("MIT_TR_URL")

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


# Worker jobs for TA1 services
def equations_to_amr(*args, **kwargs):
    equation_type = kwargs.get("equation_type")
    equations = kwargs.get("equations")
    model = kwargs.get("model")

    if equation_type == "mathml":
        # PUT the mathml to the skema endpoint.
        logger.info("Processing mathml")
        url = f"{SKEMA_API}/mathml/amr"
        put_payload = {"mathml": equations, "model": model}
    elif equation_type == "latex":
        logger.info("Processing latex")
        url = f"{UNIFIED_API}/workflows/latex/equations-to-amr"
        put_payload = {"equations": equations, "model": model}

    headers = {"Content-Type": "application/json"}    

    logger.info(f"Sending equations of type {equation_type} to TA1")
    if equation_type == "mathml":
        amr_response = requests.put(
            url, data=json.dumps(put_payload, default=str), headers=headers
        )
    elif equation_type == "latex": 
        amr_response = requests.post(
            url, data=json.dumps(put_payload, default=str), headers=headers
        )
    try:
        amr_json = amr_response.json()
    except:
        logger.error(f"Failed to parse response from TA1 Service: {amr_response.text}")

    if amr_response.status_code == 200 and amr_json:
        tds_responses = put_amr_to_tds(amr_json)

        response = {
            "status_code": amr_response.status_code,
            "amr": amr_json,
            "tds_model_id": tds_responses.get("model_id"),
            "tds_configuration_id": tds_responses.get("configuration_id"),
            "error": None,
        }

        return response
    else:
        response = {
            "status_code": amr_response.status_code,
            "amr": None,
            "tds_model_id": None,
            "tds_configuration_id": None,
            "error": amr_response.text,
        }

        return response


def pdf_to_text(*args, **kwargs):
    # Get options
    artifact_id = kwargs.get("artifact_id")

    artifact_json, downloaded_artifact = get_artifact_from_tds(
        artifact_id=artifact_id
    )  # Assumes  downloaded artifact is PDF, doesn't type check
    filename = artifact_json.get("file_names")[0]

    # Try to feed text to the unified service
    unified_text_reading_url = f"{UNIFIED_API}/text-reading/cosmos_to_json"

    put_payload = [
        ("pdf", (filename, io.BytesIO(downloaded_artifact), "application/pdf"))
    ]

    try:
        logger.info(f"Sending PDF to TA1 service with artifact id: {artifact_id}")
        response = requests.post(
            unified_text_reading_url,
            files=put_payload
        )
        logger.info(
            f"Response received from TA1 with status code: {response.status_code}"
        )
        extraction_json = response.json()
        text = ''
        for d in extraction_json:
            text += f"{d['content']}\n"
            
    except ValueError:
        return {
            "status_code": 500,
            "extraction": None,
            "artifact_id": None,
            "error": f"Extraction failure: {response.text}",
        }

    artifact_response = put_artifact_extraction_to_tds(
        artifact_id=artifact_id,
        name=artifact_json.get("name", None),
        description=artifact_json.get("description", None),
        filename=filename,
        text=text
    )

    if artifact_response.get("status") == 200:
        response = {
            "extraction_status_code": response.status_code,
            "extraction": extraction_json,
            "tds_status_code": artifact_response.get("status"),
            "error": None,
        }
    else:
        response = {
            "extraction_status_code": response.status_code,
            "extraction": extraction_json,
            "tds_status_code": artifact_response.get("status"),
            "error": "PUT extraction metadata to TDS failed, please check TDS api logs.",
        }

    return response

def pdf_extractions(*args, **kwargs):
    # Get options
    artifact_id = kwargs.get("artifact_id")
    annotate_skema = kwargs.get("annotate_skema")
    annotate_mit = kwargs.get("annotate_mit")
    name = kwargs.get("name")
    description = kwargs.get("description")

    artifact_json, downloaded_artifact = get_artifact_from_tds(
        artifact_id=artifact_id
    )  # Assumes  downloaded artifact is PDF, doesn't type check
    filename = artifact_json.get("file_names")[0]

    # Try to feed text to the unified service
    unified_text_reading_url = f"{UNIFIED_API}/text-reading/integrated-pdf-extractions?annotate_skema={annotate_skema}&annotate_mit={annotate_mit}"
    # headers = {"Content-Type": "application/json"}

    put_payload = [
        ("pdfs", (filename, io.BytesIO(downloaded_artifact), "application/pdf"))
    ]

    try:
        logger.info(f"Sending PDF to TA1 service with artifact id: {artifact_id}")
        response = requests.post(
            unified_text_reading_url,
            files=put_payload
        )
        logger.info(
            f"Response received from TA1 with status code: {response.status_code}"
        )
        extraction_json = response.json()
        outputs = extraction_json["outputs"]

        if isinstance(outputs, dict):
            if extraction_json.get("outputs", {"data": None}).get("data", None) is None:
                logger.error(f"Malformed or empty response from TA1: {extraction_json}")
                raise ValueError
            else:
                extraction_json = extraction_json.get("outputs").get("data")
        elif isinstance(outputs, list):
            if extraction_json.get("outputs")[0].get("data") is None:
                logger.error(f"Malformed or empty response from TA1: {extraction_json}")
                raise ValueError
            else:            
                extraction_json = [extraction_json.get("outputs")[0].get("data")]

    except ValueError:
        logger.error(f"Extraction for artifact {artifact_id} failed.")
        return {
            "status_code": 500,
            "extraction": None,
            "artifact_id": None,
            "error": f"Extraction failure: {response.text}",
        }
    
    artifact_response = put_artifact_extraction_to_tds(
        artifact_id=artifact_id,
        name=name if name is not None else artifact_json.get("name"),
        description=description
        if description is not None
        else artifact_json.get("description"),
        filename=filename,
        extractions=extraction_json,
        text=artifact_json['metadata'].get("text",None)
    )

    if artifact_response.get("status") == 200:
        response = {
            "extraction_status_code": response.status_code,
            "extraction": extraction_json,
            "tds_status_code": artifact_response.get("status"),
            "error": None,
        }
    else:
        response = {
            "extraction_status_code": response.status_code,
            "extraction": extraction_json,
            "tds_status_code": artifact_response.get("status"),
            "error": "PUT extraction metadata to TDS failed, please check TDS api logs.",
        }

    return response


def dataset_profiling_with_document(*args, **kwargs):
    openai_key = os.getenv("OPENAI_API_KEY")

    dataset_id = kwargs.get("dataset_id")
    artifact_id = kwargs.get("artifact_id")

    if artifact_id:
        artifact_json, downloaded_artifact = get_artifact_from_tds(artifact_id=artifact_id)
        doc_file = artifact_json['metadata'].get('text', 'There is no documentation for this dataset').encode()
    else:
        doc_file = b'There is no documentation for this dataset'
    
    logger.info(f"document file: {doc_file}")

    dataset_response, dataset_dataframe, dataset_csv_string = get_dataset_from_tds(
        dataset_id
    )
    dataset_json = dataset_response.json()

    params = {
        'gpt_key': openai_key
    }

    files = {
        'csv_file': ('csv_file', dataset_csv_string.encode()),
        'doc_file': ('doc_file', doc_file)
    }

    logger.info(f"Sending dataset {dataset_id} to MIT service")
    
    resp = requests.post(f"{MIT_API}/cards/get_data_card", params=params, files=files)
    
    logger.info(f"Response received from MIT with status: {resp.status_code}")
    logger.debug(f"MIT ANNOTATIONS: {resp.json()}")

    mit_annotations = resp.json()['DATA_PROFILING_RESULT']

    sys.stdout.flush()

    columns = []
    for c in dataset_dataframe.columns:
        annotation = mit_annotations.get(c, {})

        # parse groundings
        groundings = {'identifiers': {}}
        for g in annotation.get('dkg_groundings',[]):   
            groundings['identifiers'][g[0]] = g[1]
                
        # remove groundings from annotation object
        annotation.pop('dkg_groundings')
        annotation['groundings'] = groundings

        col = {
            "name": c,
            "data_type": "float",
            "description": annotation.get('description','').strip() ,
            "annotations": [],
            "metadata": annotation
        }
        columns.append(col)

    dataset_json["columns"] = columns

    resp = requests.put(f"{TDS_API}/datasets/{dataset_id}", json=dataset_json)
    dataset_id = resp.json()["id"]

    return resp.json()


# dccde3a0-0132-430c-afd8-c67953298f48
# 77a2dffb-08b3-4f6e-bfe5-83d27ed259c4
def link_amr(*args, **kwargs):
    artifact_id = kwargs.get("artifact_id")
    model_id = kwargs.get("model_id")

    artifact_json, downloaded_artifact = get_artifact_from_tds(artifact_id=artifact_id)

    tds_models_url = f"{TDS_API}/models/{model_id}"

    model = requests.get(tds_models_url)
    model_json = model.json()
    model_amr = model_json.get("model")

    logging.info(model_amr)

    jsonified_amr = json.dumps(model_amr).encode("utf-8")

    files = {
        "amr_file": (
            "amr.json",
            io.BytesIO(jsonified_amr),
            "application/json",
        ),
        "text_extractions_file": (
            "extractions.json",
            io.BytesIO(downloaded_artifact),
            "application/json",
        ),
    }

    params = {"amr_type": "petrinet"}

    skema_amr_linking_url = f"{UNIFIED_API}/metal/link_amr"

    response = requests.post(skema_amr_linking_url, files=files, params=params)

    if response.status_code == 200:
        enriched_amr = response.json()

        model_json["model"] = enriched_amr
        model_id = model_json.get("id")

        new_model_payload = model_json

        update_response = requests.put(
            f"{tds_models_url}/{model_id}", data=new_model_payload
        )

        return {
            "status": update_response.status_code,
            "message": "Model enriched and updated in TDS",
        }
    else:
        logging.error("Response from TA1 service was not 200")

        return {
            "status": response.status_code,
            "message": f"Response from TA1 service was not 200: {response.text}",
        }


# 60e539e4-6969-4369-a358-c601a3a583da
def code_to_amr(*args, **kwargs):
    artifact_id = kwargs.get("artifact_id")

    artifact_json, downloaded_artifact = get_artifact_from_tds(artifact_id=artifact_id)

    code_blob = downloaded_artifact.decode("utf-8")
    code_amr_workflow_url = f"{UNIFIED_API}/workflows/code/snippets-to-pn-amr"

    request_payload = {
        "files": [artifact_json.get("file_names")[0]],
        "blobs": [code_blob]
    }

    logger.info(f"Sending code to TA1 service with artifact id: {artifact_id}")
    amr_response = requests.post(
        code_amr_workflow_url, json=json.loads(json.dumps(request_payload))
    )
    logger.info(f"Response received from TA1 with status code: {amr_response.status_code}")

    amr_json = amr_response

    try:
        amr_json = amr_response.json()
    except:
        logger.error(f"Failed to parse response from TA1 Service:\n{amr_response.text}")

    if amr_response.status_code == 200 and amr_json:
        tds_responses = put_amr_to_tds(amr_json)

        response = {
            "status_code": amr_response.status_code,
            "amr": amr_json,
            "tds_model_id": tds_responses.get("model_id"),
            "tds_configuration_id": tds_responses.get("configuration_id"),
            "error": None,
        }

        return response
    else:
        logger.error(f"Code extraction failure: {amr_response.text}")
        response = {
            "status_code": amr_response.status_code,
            "amr": None,
            "tds_model_id": None,
            "tds_configuration_id": None,
            "error": amr_response.text,
        }

        return response
