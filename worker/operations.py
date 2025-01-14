import io
import itertools as it
import json
import os
import sys
import tempfile
import time
import requests
import zipfile

import pandas

from askem_extractions.data_model import AttributeCollection

from lib.auth import auth_session
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
OPENAI_API_KEY = settings.OPENAI_API_KEY
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

    logger.info(
        f"Sending equations of type {equation_type} to backend knowledge services at {url}"
    )
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
        logger.error(
            f"Failed to parse response from backend knowledge service: {amr_response.text}"
        )

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
            f"Sending document to backend knowledge service with document id {document_id} at {unified_text_reading_url}"
        )
        response = requests.post(unified_text_reading_url, files=put_payload)
        logger.info(
            f"Response received from backend knowledge service with status code: {response.status_code}"
        )
        extraction_json = response.json()
        logger.debug(f"TA 1 response object: {extraction_json}")
        text = "\n".join([record["content"] for record in extraction_json])

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
            f"Sending document to backend knowledge service with document id {document_id} at {cosmos_text_extraction_url}"
        )
        response = requests.post(
            cosmos_text_extraction_url, files=put_payload, data=data_form
        )
        logger.info(
            f"Response received from backend knowledge service with status code: {response.status_code}"
        )
        extraction_json = response.json()
        cosmos_job_id = extraction_json["job_id"]
        logger.info("COSMOS response object: %s", extraction_json)
        status_endpoint = extraction_json["status_endpoint"]
        result_endpoint = f"{extraction_json['result_endpoint']}"
        result_endpoint_text = f"{result_endpoint}/text"
        equations_endpoint = f"{result_endpoint}/extractions/equations"
        figures_endpoint = f"{result_endpoint}/extractions/figures"
        tables_endpoint = f"{result_endpoint}/extractions/tables"

        job_done = False

        for i in range(MAX_ITERATIONS):
            status = requests.get(status_endpoint)
            status_data = status.json()
            logger.info("Polled status endpoint %s times:\n%s", i + 1, status_data)
            job_done = status_data["error"] or status_data["job_completed"]
            if job_done:
                break
            time.sleep(POLLING_INTERVAL)

        if not job_done:
            logger.error("ERROR: Job not complete after %s seconds.", MAX_EXECTION_TIME)
            raise Exception(f"Job not complete after {MAX_EXECTION_TIME} seconds.")
        elif status_data["error"]:
            logger.error("An unexpected error occurred: %s", {status_data["error"]})
            raise Exception(
                f"An error occurred when processing in Cosmos: {status_data['error']}"
            )

        logger.info(f"Getting Cosmos extraction request from {result_endpoint_text}")
        text_extractions_result = requests.get(result_endpoint_text)
        logger.info(
            f"Cosmos response status code: {text_extractions_result.status_code}"
        )

        # Download the Cosmos extractions zipfile to a temporary directory
        temp_dir = tempfile.mkdtemp()
        zip_file_name = f"{document_id}_cosmos.zip"
        zip_file = os.path.join(temp_dir, zip_file_name)
        logger.info(f"Fetching Cosmos zipfile from: {result_endpoint}")
        with open(zip_file, "wb") as writer:
            writer.write(requests.get(result_endpoint).content)

        presigned_response = auth_session().get(
            f"{TDS_API}/document-asset/{document_id}/upload-url?filename={zip_file_name}"
        )
        upload_url = presigned_response.json().get("url")

        with open(zip_file, "rb") as file:
            asset_response = requests.put(upload_url, file)

        # Extract zipfile to enable asset uploading
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        # Assets requests
        logger.info(
            f"Fetching Cosmos assets from:\n"
            f"\t - {equations_endpoint}\n"
            f"\t - {figures_endpoint}\n"
            f"\t - {tables_endpoint}\n"
        )
        equations_resp = requests.get(equations_endpoint)
        figures_resp = requests.get(figures_endpoint)
        tables_resp = requests.get(tables_endpoint)
        responses = {
            "equation": equations_resp,
            "figure": figures_resp,
            "table": tables_resp,
        }

        # Checks status of responses, then adds their JSON content to
        # an iterator object if they were successful.
        assets_iterator = {}
        for key, response in responses.items():
            logger.info(f"{key} response status: {response.status_code}")
            if response.status_code >= 300:
                continue
            else:
                assets_iterator[key] = response.json()

        assets = []
        for key, value in assets_iterator.items():
            for record in value:
                path = record.get("img_pth", None)
                if path:
                    file_name = path.split("/")[-1]  # Gets file name from json.

                    file_name_path = os.path.join(temp_dir, file_name)
                    presigned_response = auth_session().get(
                        f"{TDS_API}/document-asset/{document_id}/upload-url?filename={file_name}"
                    )
                    upload_url = presigned_response.json().get("url")

                    with open(file_name_path, "rb") as file:
                        asset_response = requests.put(upload_url, file)

                        if asset_response.status_code >= 300:
                            raise Exception(
                                (
                                    "Failed to upload file to TDS "
                                    f"(status: {asset_response.status_code}): {file_name}"
                                )
                            )
                else:
                    logger.error(f"No img_pth key for {record}")

                asset_object = {
                    "file_name": file_name,
                    "asset_type": key,
                    "metadata": record,
                }

                assets.append(asset_object)

        logger.debug(f"Cosmos result response: {text_extractions_result.text[80:]}")

        logger.debug(f"Assets payload: {assets}")

        extraction_json = text_extractions_result.json()
        text = "\n".join([record["content"] for record in extraction_json])

    except ValueError as ve:
        logger.error(f"Value Error: {ve}")
        raise Exception(
            f"Extraction failure: {response.text}"
            f"with status code {response.status_code}"
        ) from None

    try:
        temp_dir.cleanup()
    except AttributeError:
        logger.info(
            "Temporary directory not directly cleaned, should be remove when code finishes execution."
        )
        logger.debug(
            "If worker is getting large, check if temporary files are being removed."
        )

    return (
        text,
        response.status_code,
        extraction_json,
        assets,
        zip_file_name,
        cosmos_job_id,
    )


def pdf_extraction(*args, **kwargs):
    # Get options
    document_id = kwargs.get("document_id")
    force_run = kwargs.get("force_run")

    document_json, downloaded_document = get_document_from_tds(
        document_id=document_id
    )  # Assumes  downloaded document is PDF, doesn't type check
    filename = document_json.get("file_names")[0]

    match settings.PDF_EXTRACTOR:
        case ExtractionServices.SKEMA:
            text, status_code, extraction_json = skema_extraction(
                document_id=document_id,
                filename=filename,
                downloaded_document=downloaded_document,
            )
            assets = None
        case ExtractionServices.COSMOS:
            (
                text,
                status_code,
                extraction_json,
                assets,
                zip_file_name,
                cosmos_job_id,
            ) = cosmos_extraction(
                document_id=document_id,
                force_run=force_run,
                filename=filename,
                downloaded_document=downloaded_document,
            )

    document_response = put_document_extraction_to_tds(
        document_id=document_id,
        name=document_json.get("name", None),
        description=document_json.get("description", None),
        filename=filename,
        text=text,
        assets=assets,
        zip_file_name=zip_file_name,
    )

    if document_response.get("status") == 200:
        response = {
            "extraction_status_code": status_code,
            "extraction": extraction_json,
            "tds_status_code": document_response.get("status"),
            "cosmos_job_id": cosmos_job_id,
        }
    else:
        raise Exception(
            f"PUT extraction metadata to TDS failed with status"
            f"{document_response.get('status')} please check TDS api logs."
        ) from None

    return response


def variable_extractions(*args, **kwargs):
    # Get options
    document_id = kwargs.get("document_id")
    annotate_skema = kwargs.get("annotate_skema")
    annotate_mit = kwargs.get("annotate_mit")
    name = kwargs.get("name")
    description = kwargs.get("description")
    kg_domain = kwargs.get("domain", "epi")

    document_json, downloaded_document = get_document_from_tds(document_id=document_id)

    text = document_json.get("text", None)
    if not text:
        raise Exception(
            "No text found in paper document, please ensure to submit to /pdf_extraction endpoint."
        )

    # Send document to SKEMA
    if annotate_skema:
        unified_text_reading_url = f"{UNIFIED_API}/text-reading/integrated-text-extractions?annotate_skema={annotate_skema}&annotate_mit=False"
        payload = {"texts": [text]}

        try:
            logger.info(
                f"Sending document to SKEMA service with document id {document_id} at {unified_text_reading_url}"
            )
            skema_response = requests.post(unified_text_reading_url, json=payload)
            logger.info(
                f"Response received from SKEMA service with status code: {skema_response.status_code}"
            )
            skema_extraction_json = skema_response.json()
            logger.debug(f"SKEMA variable response object: {skema_response.text}")

        except Exception as e:
            logger.error(f"SKEMA variable extraction for document {document_id} failed.")

    # Send document to MIT
    if annotate_mit:
        mit_text_reading_url = f"{MIT_API}/annotation/upload_file_extract"
        files = {
            "file": text.encode(),
        }
        params = {"gpt_key": OPENAI_API_KEY, "kg_domain": kg_domain}

        try:
            logger.info(
                f"Sending document to MIT service with document id {document_id} at {mit_text_reading_url}"
            )
            mit_response = requests.post(mit_text_reading_url, params=params, files=files)
            logger.info(
                f"Response received from MIT service with status code: {mit_response.status_code}"
            )
            mit_extraction_json = mit_response.json()
            logger.debug(f"MIT variable response object: {mit_response.text}")

        except Exception as e:
            logger.error(f"MIT variable extraction for document {document_id} failed.")

    # TODO: implement merging code here that generates
    collections = list()

    try:
        skema_collection = AttributeCollection.from_json(skema_extraction_json['outputs'][0]['data'])
        collections.append(skema_collection)
    except Exception as e:
        logger.error(f"Error generating collection from SKEMA variable extractions: {e}")
        skema_collection = None

    try:
        mit_collection = AttributeCollection.from_json(mit_extraction_json)
        collections.append(mit_collection)
    except Exception as e:
        logger.error(f"Error generating collection from MIT variable extractions: {e}")
        mit_collection = None

    if not bool(skema_collection and mit_collection):
        logger.info("Falling back on single variable extraction since one system failed")
        attributes = list(it.chain.from_iterable(c.attributes for c in collections))
        variables = AttributeCollection(attributes=attributes)
    else:
        # Merge both with some de de-duplications
        params = {"gpt_key": OPENAI_API_KEY}

        data = {
            "mit_file": json.dumps(mit_extraction_json),
            "arizona_file": json.dumps(skema_extraction_json['outputs'][0]['data']),
        }
        logger.info("Sending variable merging request to MIT")
        print('sending to MIT')
        response = requests.post(
            f"{MIT_API}/integration/get_mapping", params=params, files=data
        )

        # MIT merges the collection for us
        if response.status_code == 200:
            variables = AttributeCollection.from_json(response.json())
        else:
            # Fallback to collection
            logger.info(f"MIT merge failed: {response.text}")
            attributes = list(it.chain.from_iterable(c.attributes for c in collections))
            variables = AttributeCollection(attributes=attributes)

    if len(document_json.get("file_names")) > 1:
        zip_file_name = document_json.get("file_names")[1]
    else:
        zip_file_name = None

    extraction_json = json.loads(variables.json())

    if len(document_json.get("file_names")) > 1:
        zip_file_name = document_json.get("file_names")[1]
    else:
        zip_file_name = None

    document_response = put_document_extraction_to_tds(
        document_id=document_id,
        name=name if name is not None else document_json.get("name"),
        description=description
        if description is not None
        else document_json.get("description"),
        filename=document_json.get("file_names")[0],
        zip_file_name=zip_file_name,
        extractions=extraction_json,
        text=document_json.get("text", None),
        assets=document_json.get("assets", None),
    )

    logger.info(f"DOC RESPONSE VAR EXTRACTION: {document_response}")

    if document_response.get("status") == 200:
        response = {
            "extraction": extraction_json,
            "tds_status_code": document_response.get("status"),
            "error": None,
        }
        if annotate_skema:
            response["skema_extraction_status_code"] = skema_response.status_code
        else:
            response["skema_extraction_status_code"] = None

        if annotate_mit:
            response["mit_extraction_status_code"] = mit_response.status_code
        else:
            response["mit_extraction_status_code"] = None
    else:
        raise Exception(
            f"PUT extraction metadata to TDS failed with status"
            f"{document_response.get('status')} please check TDS api logs."
        ) from None

    return response


def data_card(*args, **kwargs):
    dataset_id = kwargs.get("dataset_id")
    document_id = kwargs.get("document_id")

    if document_id:
        document_json, downloaded_document = get_document_from_tds(
            document_id
        )
        doc_file = document_json.get(
            "text", "There is no documentation for this dataset"
        ).encode()
    else:
        doc_file = b"There is no documentation for this dataset"

    logger.debug(f"document file: {doc_file}")

    dataset_response, dataset_dataframe, dataset_csv_string = get_dataset_from_tds(
        dataset_id
    )
    dataset_json = dataset_response.json()

    params = {"gpt_key": OPENAI_API_KEY}

    files = {
        "csv_file": ("csv_file", dataset_csv_string.encode()),
        "doc_file": ("doc_file", doc_file),
    }

    url = f"{MIT_API}/cards/get_data_card"
    logger.info(f"Sending dataset {dataset_id} and document {document_id} to MIT service at {url}")
    resp = requests.post(url, params=params, files=files)
    if resp.status_code != 200:
        raise Exception(f"Failed response from MIT: {resp.status_code}, {resp.text}")

    logger.info(f"Response received from MIT with status: {resp.status_code}")
    logger.debug(f"TA 1 response object: {resp.json()}")

    data_card = resp.json()
    data_profiling_result = data_card["DATA_PROFILING_RESULT"]

    sys.stdout.flush()

    columns = []
    for c in dataset_dataframe.columns:
        annotation = data_profiling_result.get(c, {})

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

    if dataset_json.get("metadata") is None:
        dataset_json["metadata"] = {}

    if dataset_json["metadata"].get("data_card") is None:
        dataset_json["metadata"]["data_card"] = {}

    dataset_json["metadata"]["data_card"] = data_card

    tds_resp = auth_session().put(f"{TDS_API}/datasets/{dataset_id}", json=dataset_json)
    if tds_resp.status_code != 200:
        raise Exception(
            f"PUT extraction metadata to TDS failed with status please check TDS api logs: {tds_resp.status_code}"
        ) from None

    return {
        "status": tds_resp.status_code,
        "data_card": dataset_json["metadata"]["data_card"],
        "message": "Data card generated and updated in TDS",
    }


def model_card(*args, **kwargs):
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

    if paper_document_id:
        paper_document_json, paper_downloaded_document = get_document_from_tds(
            document_id=paper_document_id
        )

        text_file = (
            paper_document_json.get("text")
            or "There is no documentation for this model"
        )
    else:
        text_file = "There is no documentation for this model"

    # TODO: Remove when no character limit exists for MIT
    text_file = text_file[:9000]

    amr = get_model_from_tds(model_id).json()

    params = {"gpt_key": OPENAI_API_KEY}

    files = {
        "text_file": text_file.encode(),
        "code_file": code_file.encode(),
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

            tds_resp = auth_session().put(f"{TDS_API}/models/{model_id}", json=amr)
            if tds_resp.status_code == 200:
                logger.info(f"Updated model {model_id} in TDS: {tds_resp.status_code}")
                return {
                    "status": tds_resp.status_code,
                    "message": "Model card generated and updated in TDS",
                    "card": card,
                }
            else:
                raise Exception(
                    f"Error when updating model {model_id} in TDS: {tds_resp.status_code}"
                )
        except Exception as e:
            raise Exception(f"Failed to generate model card for {model_id}: {e}")

    else:
        raise Exception(
            f"Bad response from TA1 service for {model_id}: {resp.status_code} \n {resp.content}"
        )


def link_amr(*args, **kwargs):
    document_id = kwargs.get("document_id")
    model_id = kwargs.get("model_id")

    document_json, downloaded_document = get_document_from_tds(document_id=document_id)

    extractions = document_json.get("metadata", {})

    tds_model_url = f"{TDS_API}/models/{model_id}"

    model = auth_session().get(tds_model_url)
    model_json = model.json()
    model_amr = model_json
    model_card = model_amr.get('metadata',{}).get('card')

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
    logger.info(
        f"Sending model {model_id} and document {document_id} for linking to: {skema_amr_linking_url}"
    )
    response = requests.post(skema_amr_linking_url, files=files, params=params)
    logger.info(f"SKEMA response status code: {response.status_code}")
    logger.debug(f"TA 1 response object: {response.text}")

    if response.status_code == 200:
        enriched_amr = response.json()
        enriched_amr['metadata']['card'] = model_card

        model_response = auth_session().put(tds_model_url, json=enriched_amr)
        if model_response.status_code != 200:
            raise Exception(
                f"Cannot update model {model_id} in TDS with payload:\n\n {enriched_amr}"
            )
        logger.info(f"Updated enriched model in TDS with id {model_id}")

        model_amr.update(enriched_amr)

        logger.info(f"Setting provenance between model {model_id} and document {document_id}")
        try:
            set_provenance(
                model_id,
                "Model",
                document_id,
                "Document",
                "EXTRACTED_FROM",
                )
        except Exception as e:
            logger.error(f"Failed to set provenance between model {model_id} and document {document_id}: {e}")

        return {
            "status": model_response.status_code,
            "amr": model_amr,
            "message": "Model enriched and updated in TDS",
        }
    else:
        raise Exception(
            f"Response from backend knowledge service was not 200: {response.text}"
        )


# 60e539e4-6969-4369-a358-c601a3a583da
def code_to_amr(*args, **kwargs):
    code_id = kwargs.get("code_id")
    name = kwargs.get("name")
    model_id = kwargs.get("model_id")
    description = kwargs.get("description")
    llm_assisted = kwargs.get("llm_assisted", True)
    dynamics_only = kwargs.get("dynamics_only", False)

    code_json, downloaded_code_object, dynamics_off_flag = get_code_from_tds(
        code_id, code=True, dynamics_only=dynamics_only
    )

    # Checks the return flag from the dynamics retrieval process
    if dynamics_off_flag:
        dynamics_only = False

    # default to using LLM assisted extraction
    code_amr_workflow_url = f"{UNIFIED_API}/workflows/code/llm-assisted-codebase-to-pn-amr"
    if not llm_assisted:
        code_amr_workflow_url = f"{UNIFIED_API}/workflows/code/codebase-to-pn-amr"
    if dynamics_only:
        code_amr_workflow_url = f"{UNIFIED_API}/workflows/code/snippets-to-pn-amr"


    if dynamics_only:
        blobs = []
        names = []
        for code_name, code_content in downloaded_code_object.items():
            names.append(code_name)
            blobs.extend(code_content)
        request_payload = {
            "files": names,
            "blobs": blobs,
        }

    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Use io and zipfile to write the code_content to a zipfile in memory
            for code_name, code_content in downloaded_code_object.items():
                try:
                    zipf.writestr(code_name, code_content.decode("utf-8"))
                except UnicodeDecodeError as e:
                    logging.error(
                        f"File unable to be decoded with utf-8 and written to zip, skipping. {e}"
                    )

        zip_buffer.seek(0)
        request_payload = zip_buffer

    logger.info(
        f"Sending code to knowledge service with code id: {code_id} at {code_amr_workflow_url}"
    )

    logger.info(f"Request payload: {request_payload}")
    if isinstance(request_payload, dict):
        # dynamics only
        amr_response = requests.post(
            code_amr_workflow_url, json=json.loads(json.dumps(request_payload))
        )
    else:
        files = {
            "zip_file": ("zip_file.zip", request_payload.read(), "application/zip")
        }
        amr_response = requests.post(code_amr_workflow_url, files=files)
    logger.info(
        f"Response received from backend knowledge service with status code: {amr_response.status_code}"
    )

    amr_json = amr_response

    try:
        amr_json = amr_response.json()
        logger.debug(f"TA 1 response object: {amr_json}")
    except:
        logger.error(
            f"Failed to parse response from backend knowledge service:\n{amr_response.text}"
        )

    if amr_response.status_code == 200 and amr_json:
        metadata = amr_json.get("metadata", {})
        metadata["code_id"] = code_id
        amr_json["metadata"] = metadata
        tds_responses = put_amr_to_tds(amr_json, name, description, model_id)
        logger.info(f"TDS Response: {tds_responses}")

        put_code_extraction_to_tds(
            code_id=code_id,
            name=code_json.get("name", None),
            files=code_json.get("files"),
            description=code_json.get("description", None),
            model_id=tds_responses.get("model_id"),
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
            logger.error(f"Failed to store provenance tying model to code: {e}")

        response = {
            "status_code": amr_response.status_code,
            "amr": amr_json,
            "tds_model_id": tds_responses.get("model_id"),
            "tds_configuration_id": tds_responses.get("configuration_id"),
            "error": None,
        }

        return response
    else:
        logger.error(f"Content: {amr_response.content}")
        raise Exception(f"Code extraction failure: {amr_response.text}")
