import io
import json
import os
import sys
import time

import requests
from worker.utils import (
    find_source_code,
    get_code_from_tds,
    get_document_from_tds,
    get_dataset_from_tds,
    get_model_from_tds,
    put_amr_to_tds,
    put_code_extraction_to_tds,
    put_document_extraction_to_tds,
    set_provenance,
)
from lib.settings import settings, ExtractionServices

TDS_API = settings.TDS_URL
SKEMA_API = settings.SKEMA_RS_URL
UNIFIED_API = settings.TA1_UNIFIED_URL
MIT_API = settings.MIT_TR_URL
LOG_LEVEL = settings.LOG_LEVEL.upper()

import logging

numeric_level = getattr(logging, LOG_LEVEL, None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {LOG_LEVEL}")

logger = logging.getLogger(__name__)
logger.setLevel(numeric_level)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - [%(lineno)d] - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


# Worker jobs for knowledge services
def equations_to_amr(*args, **kwargs):
    equation_type = kwargs.get("equation_type")
    equations = kwargs.get("equations")
    model = kwargs.get("model")
    model_id = kwargs.get("model_id")
    name = kwargs.get("name")
    description = kwargs.get("description")

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

    logger.info(f"Sending equations of type {equation_type} to backend knowledge services at {url}")
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
        logger.debug(f"TA 1 response object: {amr_response}")
    except:
        logger.error(f"Failed to parse response from backend knowledge service: {amr_response.text}")

    if amr_response.status_code == 200 and amr_json:
        tds_responses = put_amr_to_tds(amr_json, name, description, model_id)

        response = {
            "status_code": amr_response.status_code,
            "amr": amr_json,
            "tds_model_id": tds_responses.get("model_id"),
            "tds_configuration_id": tds_responses.get("configuration_id"),
            "error": None,
        }

        return response
    else:
        raise Exception(
            f"Error encountered converting equations to text: {amr_response.text}"
        ) from None


def skema_extraction(document_id, filename, downloaded_document):
    # Try to feed text to the unified service
    unified_text_reading_url = f"{UNIFIED_API}/text-reading/cosmos_to_json"

    put_payload = [
        ("pdf", (filename, io.BytesIO(downloaded_document), "application/pdf"))
    ]

    try:
        logger.info(
            f"Sending PDF to backend knowledge service with document id {document_id} at {unified_text_reading_url}"
        )
        response = requests.post(unified_text_reading_url, files=put_payload)
        logger.info(
            f"Response received from backend knowledge service with status code: {response.status_code}"
        )
        extraction_json = response.json()
        logger.debug(f"TA 1 response object: {extraction_json}")
        text = "\n".join([
           record["content"] for record in extraction_json
        ])

    except ValueError:
        raise Exception(
            f"Extraction failure: {response.text}"
            f"with status code {response.status_code}"
        ) from None

    return text, response.status_code, extraction_json

def cosmos_extraction(document_id, filename, downloaded_document, force_run=False):
    MAX_EXECTION_TIME = 600
    POLLING_INTERVAL = 5
    MAX_ITERATIONS = MAX_EXECTION_TIME // POLLING_INTERVAL

    cosmos_text_extraction_url = f"{settings.COSMOS_URL}/process/"

    put_payload = [
        ("pdf", (filename, io.BytesIO(downloaded_document), "application/pdf"))
    ]
    data_form = {
        "compress_images": False,
        "use_cache": (not force_run),
    }

    try:
        logger.info(
            f"Sending PDF to backend knowledge service with document id {document_id} at {cosmos_text_extraction_url}"
        )
        response = requests.post(cosmos_text_extraction_url, files=put_payload, data=data_form)
        logger.info(
            f"Response received from backend knowledge service with status code: {response.status_code}"
        )
        extraction_json = response.json()
        logger.debug("COSMOS response object: %s", extraction_json)
        status_endpoint = extraction_json["status_endpoint"]
        result_endpoint = f"{extraction_json['result_endpoint']}/text"

        job_done = False

        for i in range(MAX_ITERATIONS):
            status = requests.get(status_endpoint)
            status_data = status.json()
            logger.info("Polled status endpoint %s times:\n%s", i+1, status_data)
            job_done = status_data['error'] or status_data['job_completed']
            if job_done:
                break
            time.sleep(POLLING_INTERVAL)

        if not job_done:
            logger.error("ERROR: Job not complete after %s seconds.", MAX_EXECTION_TIME)
            raise Exception(f"Job not complete after {MAX_EXECTION_TIME} seconds.")
        elif status_data['error']:
            logger.error("An unexpected error occurred: %s", {status_data["error"]})
            raise Exception(f"An error occurred when processing in Cosmos: {status_data['error']}")

        result = requests.get(result_endpoint)
        logger.debug(f"result response: %s", result.text[80:])

        extraction_json = result.json()
        text = "\n".join([
           record["content"] for record in extraction_json
        ])

    except ValueError:
        raise Exception(
            f"Extraction failure: {response.text}"
            f"with status code {response.status_code}"
        ) from None

    return text, response.status_code, extraction_json


def pdf_to_text(*args, **kwargs):
    # Get options
    document_id = kwargs.get("document_id")

    document_json, downloaded_document = get_document_from_tds(
        document_id=document_id
    )  # Assumes  downloaded document is PDF, doesn't type check
    filename = document_json.get("file_names")[0]

    match settings.PDF_EXTRACTOR:
        case ExtractionServices.SKEMA:
            text, status_code, extraction_json = skema_extraction(
                document_id=document_id,
                filename=filename,
                downloaded_document=downloaded_document
            )
        case ExtractionServices.COSMOS:
            text, status_code, extraction_json = cosmos_extraction(
                document_id=document_id,
                filename=filename,
                downloaded_document=downloaded_document
            )

    document_response = put_document_extraction_to_tds(
        document_id=document_id,
        name=document_json.get("name", None),
        description=document_json.get("description", None),
        filename=filename,
        text=text,
    )

    if document_response.get("status") == 200:
        response = {
            "extraction_status_code": status_code,
            "extraction": extraction_json,
            "tds_status_code": document_response.get("status"),
        }
    else:
        raise Exception(
            f"PUT extraction metadata to TDS failed with status"
            f"{document_response.get('status')} please check TDS api logs."
        ) from None

    return response


def pdf_extractions(*args, **kwargs):
    # Get options
    document_id = kwargs.get("document_id")
    annotate_skema = kwargs.get("annotate_skema")
    annotate_mit = kwargs.get("annotate_mit")
    name = kwargs.get("name")
    description = kwargs.get("description")

    document_json, downloaded_document = get_document_from_tds(document_id=document_id)

    text = document_json.get("text", None)
    if not text:
        raise Exception(
            "No text found in paper document, please ensure to submit to /pdf_to_text endpoint."
        )

    # Try to feed text to the unified service
    unified_text_reading_url = f"{UNIFIED_API}/text-reading/integrated-text-extractions?annotate_skema={annotate_skema}&annotate_mit={annotate_mit}"
    payload = {"texts": [text]}

    try:
        logger.info(
            f"Sending PDF to backend knowledge service with document id {document_id} at {unified_text_reading_url}"
        )
        response = requests.post(unified_text_reading_url, json=payload)
        logger.info(
            f"Response received from backend knowledge service with status code: {response.status_code}"
        )
        extraction_json = response.json()
        logger.debug(f"TA 1 response object: {response.text}")
        outputs = extraction_json["outputs"]

        if isinstance(outputs, dict):
            if extraction_json.get("outputs", {"data": None}).get("data", None) is None:
                raise ValueError(
                    f"Malformed or empty response from backend knowledge service: {extraction_json}"
                )
            else:
                extraction_json = extraction_json.get("outputs").get("data")
        elif isinstance(outputs, list):
            if extraction_json.get("outputs")[0].get("data") is None:
                raise ValueError(
                    f"Malformed or empty response from backend knowledge service: {extraction_json}"
                )
            else:
                extraction_json = [extraction_json.get("outputs")[0].get("data")]
                logging.info("HERE!")

    except ValueError:
        raise ValueError(f"Extraction for document {document_id} failed.")

    document_response = put_document_extraction_to_tds(
        document_id=document_id,
        name=name if name is not None else document_json.get("name"),
        description=description
        if description is not None
        else document_json.get("description"),
        filename=document_json.get("file_names")[0],
        extractions=extraction_json,
        text=document_json.get("text", None),
    )

    if document_response.get("status") == 200:
        response = {
            "extraction_status_code": response.status_code,
            "extraction": extraction_json,
            "tds_status_code": document_response.get("status"),
            "error": None,
        }
    else:
        raise Exception(
            f"PUT extraction metadata to TDS failed with status"
            f"{document_response.get('status')} please check TDS api logs."
        ) from None

    return response


def data_card(*args, **kwargs):
    openai_key = settings.OPENAI_API_KEY

    dataset_id = kwargs.get("dataset_id")
    artifact_id = kwargs.get("artifact_id")

    if artifact_id:
        document_json, downloaded_artifact = get_document_from_tds(
            document_id=artifact_id
        )
        doc_file = (
            document_json
            .get("text", "There is no documentation for this dataset")
            .encode()
        )
    else:
        doc_file = b"There is no documentation for this dataset"

    logger.debug(f"document file: {doc_file}")

    dataset_response, dataset_dataframe, dataset_csv_string = get_dataset_from_tds(
        dataset_id
    )
    dataset_json = dataset_response.json()

    params = {"gpt_key": openai_key}

    files = {
        "csv_file": ("csv_file", dataset_csv_string.encode()),
        "doc_file": ("doc_file", doc_file),
    }

    url = f"{MIT_API}/cards/get_data_card"
    logger.info(f"Sending dataset {dataset_id} to MIT service at {url}")
    resp = requests.post(url, params=params, files=files)
    if resp.status_code != 200:
        raise Exception(f"Failed response from MIT: {resp.status_code}, {resp.text}")

    logger.info(f"Response received from MIT with status: {resp.status_code}")
    logger.debug(f"TA 1 response object: {resp.json()}")

    mit_annotations = resp.json()["DATA_PROFILING_RESULT"]

    sys.stdout.flush()

    columns = []
    for c in dataset_dataframe.columns:
        annotation = mit_annotations.get(c, {})

        # parse groundings
        groundings = {"identifiers": {}}
        for g in annotation.get("dkg_groundings", []):
            groundings["identifiers"][g[0]] = g[1]

        # remove groundings from annotation object
        annotation.pop("dkg_groundings")
        annotation["groundings"] = groundings

        col = {
            "name": c,
            "data_type": "float",
            "description": annotation.get("description", "").strip(),
            "annotations": [],
            "metadata": annotation,
        }
        columns.append(col)

    dataset_json["columns"] = columns

    tds_resp = requests.put(f"{TDS_API}/datasets/{dataset_id}", json=dataset_json)
    if tds_resp.status_code != 200:
        raise Exception(
            f"PUT extraction metadata to TDS failed with status please check TDS api logs: {tds_resp.status_code}"
        ) from None

    return {
        "status": tds_resp.status_code,
        "message": "Data card generated and updated in TDS",
    }


def model_card(*args, **kwargs):
    openai_key = settings.OPENAI_API_KEY
    model_id = kwargs.get("model_id")
    paper_document_id = kwargs.get("paper_document_id")

    try:
        code_artifact_id = find_source_code(model_id)
        if code_artifact_id:
            code_artifact_json, code_downloaded_artifact = get_code_from_tds(
                code_id=code_artifact_id
            )
            code_file = code_downloaded_artifact.decode("utf-8")
        else:
            logger.info(f"No associated code artifact found for model {model_id}")
            code_file = "No available code associated with model."
    except Exception as e:
        # TODO: Figure how how to assert that we are properly finding the code file in tests
        logger.error(f"Issue finding associated source code: {e}")
        code_file = "No available code associated with model."

    logger.debug(f"Code file head (250 chars): {code_file[:250]}")

    paper_document_json, paper_downloaded_document = get_document_from_tds(
        document_id=paper_document_id
    )
    text_file = (
        paper_document_json
        .get("text", "There is no documentation for this model")
        .encode()
    )

    amr = get_model_from_tds(model_id).json()

    params = {"gpt_key": openai_key}

    files = {
        "text_file": ("text_file", text_file),
        "code_file": ("doc_file", code_file),
    }

    url = f"{MIT_API}/cards/get_model_card"
    logger.info(f"Sending model {model_id} to MIT service at {url}")

    resp = requests.post(url, params=params, files=files)
    logger.info(f"Response received from MIT with status: {resp.status_code}")
    logger.debug(f"TA 1 response object: {resp.json()}")

    if resp.status_code == 200:
        try:
            card = resp.json()
            sys.stdout.flush()

            amr["description"] = card.get("DESCRIPTION")
            if not amr.get("metadata", None):
                amr["metadata"] = {"card": card}
            else:
                amr["metadata"]["card"] = card

            tds_resp = requests.put(f"{TDS_API}/models/{model_id}", json=amr)
            if tds_resp.status_code == 200:
                logger.info(f"Updated model {model_id} in TDS: {tds_resp.status_code}")
                return {
                    "status": tds_resp.status_code,
                    "message": "Model card generated and updated in TDS",
                    "card": card
                }
            else:
                raise Exception(
                    f"Error when updating model {model_id} in TDS: {tds_resp.status_code}"
                )
        except Exception as e:
            raise Exception(f"Failed to generate model card for {model_id}: {e}")

    else:
        raise Exception(f"Bad response from TA1 service for {model_id}: {resp.status_code}")


def link_amr(*args, **kwargs):
    document_id = kwargs.get("document_id")
    model_id = kwargs.get("model_id")

    document_json, downloaded_document = get_document_from_tds(
        document_id=document_id
    )

    extractions = document_json.get('metadata',{})

    tds_model_url = f"{TDS_API}/models/{model_id}"

    model = requests.get(tds_model_url)
    model_json = model.json()
    model_amr = model_json

    logging.debug(model_amr)

    stringified_amr = json.dumps(model_amr).encode("utf-8")
    stringified_extractions = json.dumps(extractions).encode("utf-8")

    files = {
        "amr_file": (
            "amr.json",
            io.BytesIO(stringified_amr),
            "application/json",
        ),
        "text_extractions_file": (
            "extractions.json",
            io.BytesIO(stringified_extractions),
            "application/json",
        ),
    }

    params = {"amr_type": "petrinet"}

    skema_amr_linking_url = f"{UNIFIED_API}/metal/link_amr"
    logger.info(f"Sending model {model_id} and document {document_id} for linking")
    response = requests.post(skema_amr_linking_url, files=files, params=params)
    logger.debug(f"TA 1 response object: {response.text}")

    if response.status_code == 200:
        enriched_amr = response.json()

        model_response = requests.put(tds_model_url, json=enriched_amr)
        if model_response.status_code != 200:
            raise Exception(
                f"Cannot update model {model_id} in TDS with payload:\n\n {enriched_amr}"
            )
        logger.info(f"Updated enriched model in TDS with id {model_id}")

        model_amr.update(enriched_amr)

        return {
            "status": model_response.status_code,
            "amr": model_amr,            
            "message": "Model enriched and updated in TDS",
        }
    else:
        raise Exception(f"Response from backend knowledge service was not 200: {response.text}")


# 60e539e4-6969-4369-a358-c601a3a583da
def code_to_amr(*args, **kwargs):
    code_id = kwargs.get("code_id")
    name = kwargs.get("name")
    description = kwargs.get("description")

    code_json, downloaded_code = get_code_from_tds(code_id, code=True)

    code_blob = downloaded_code.decode("utf-8")
    logger.info(code_blob[:250])
    code_amr_workflow_url = f"{UNIFIED_API}/workflows/code/snippets-to-pn-amr"

    request_payload = {
        "files": [code_json.get("filename")],
        "blobs": [code_blob],
    }

    logger.info(
        f"Sending code to knowledge service with code id: {code_id} at {code_amr_workflow_url}"
    )
    amr_response = requests.post(
        code_amr_workflow_url, json=json.loads(json.dumps(request_payload))
    )
    logger.info(
        f"Response received from backend knowledge service with status code: {amr_response.status_code}"
    )

    amr_json = amr_response

    try:
        amr_json = amr_response.json()
        logger.debug(f"TA 1 response object: {amr_json}")
    except:
        logger.error(f"Failed to parse response from backend knowledge service:\n{amr_response.text}")

    if amr_response.status_code == 200 and amr_json:
        metadata = amr_json.get("metadata",{})
        metadata["code_id"] = code_id
        amr_json["metadata"] = metadata
        tds_responses = put_amr_to_tds(amr_json, name, description)
        logger.info(f"TDS Response: {tds_responses}")

        put_code_extraction_to_tds(
            code_id=code_id,
            name=code_json.get("name", None),
            filename=code_json.get("filename"),
            description=code_json.get("description", None),
            model_id=tds_responses.get("model_id"),
            code_language=code_json.get("language")
        )

        try:
            set_provenance(
                tds_responses.get("model_id"),
                "Model",
                code_id,
                "Code",
                "EXTRACTED_FROM",
            )
        except Exception as e:
            logger.error(
                f"Failed to store provenance tying model to code: {e}"
            )

        response = {
            "status_code": amr_response.status_code,
            "amr": amr_json,
            "tds_model_id": tds_responses.get("model_id"),
            "tds_configuration_id": tds_responses.get("configuration_id"),
            "error": None,
        }

        return response
    else:
        raise Exception(f"Code extraction failure: {amr_response.text}")
