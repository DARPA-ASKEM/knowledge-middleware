import io
import json
import os
import sys
import logging

import pandas
import requests

from lib.settings import settings

LOG_LEVEL = settings.LOG_LEVEL.upper()


numeric_level = getattr(logging, LOG_LEVEL, None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {LOG_LEVEL}")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - [%(lineno)d] - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

TDS_API = settings.TDS_URL


def put_amr_to_tds(amr_payload, name=None, description=None, model_id=None):
    # Expects json amr payload and puts it to TDS models and model-configurations, returning an ID.

    headers = {"Content-Type": "application/json"}

    if name:
        amr_payload["header"]["name"] = name
    if description:
        amr_payload["header"]["description"] = description
    if model_id:
        amr_payload["id"] = model_id

    logger.debug(amr_payload)

    # Update model if it exists in TDS already.
    if model_id:
        tds_models = f"{TDS_API}/models/{model_id}"

        model_response = requests.get(tds_models, headers=headers)
        if model_response.status_code != 200:
            raise Exception(f"Cannot fetch model {model_id} in TDS")

        # Keep name and information from existing model
        fetched_amr = model_response.json()
        amr_payload["header"]["name"] = fetched_amr.get("header", {}).get("name", None)
        amr_payload["header"]["description"] = fetched_amr.get("header", {}).get(
            "description", None
        )

        update_model_response = requests.put(
            tds_models, json=amr_payload, headers=headers
        )
        if update_model_response.status_code != 200:
            raise Exception(
                f"Cannot update model {model_id} in TDS with payload:\n\n {amr_payload}"
            )
        logger.info(f"Updated model in TDS with id {model_id}")

    # Create TDS model
    else:
        tds_models = f"{TDS_API}/models"
        model_response = requests.post(tds_models, json=amr_payload, headers=headers)

        model_id = model_response.json().get("id")

        logger.info(f"Created model in TDS with id {model_id}")

    # Create TDS model configuration
    tds_model_configurations = TDS_API + "/model_configurations"
    header = amr_payload.get("header", {})
    configuration_payload = {
        "model_id": model_id,
        "name": "Default config",
        "description": header.get("description", amr_payload.get("description")),
        "model_version": header.get("model_version", amr_payload.get("model_version")),
        "calibrated": False,
        "configuration": json.loads(json.dumps(amr_payload)),
    }

    config_response = requests.post(
        tds_model_configurations,
        data=json.dumps(configuration_payload, default=str),
        headers=headers,
    )

    config_id = config_response.json().get("id")

    logger.info(f"Created model config in TDS with id {config_id}")
    return {"model_id": model_id, "configuration_id": config_id}


def put_document_extraction_to_tds(
    document_id,
    name,
    description,
    filename,
    extractions=None,
    text=None,
    model_id=None,
    assets=None,
    zip_file_name=None,
):
    """
    Update an document or code object in TDS.
    """
    if extractions and text:
        metadata = extractions
    elif extractions:
        metadata = extractions
    elif model_id:
        metadata = {"model_id": model_id}
    else:
        metadata = {}

    if zip_file_name:
        file_names = [filename, zip_file_name]
    else:
        file_names = [filename]

    document_payload = {
        "username": "extraction_service",
        "name": name,
        "description": description,
        "file_names": file_names,
        "text": text,
        "metadata": metadata,
        "assets": assets,
    }

    logger.debug(f"Payload going to TDS: {document_payload}")
    logger.info(f"Storing document to TDS: {document_id}")
    # Update document in TDS
    document_url = f"{TDS_API}/documents/{document_id}"
    document_response = requests.put(document_url, json=document_payload)
    logger.debug(f"TDS response: {document_response.text}")
    document_put_status = document_response.status_code

    return {"status": document_put_status}


def put_code_extraction_to_tds(
    code_id,
    name,
    description,
    files,
    extractions=None,
    text=None,
    model_id=None,
):
    """
    Update a code object in TDS.
    """
    if extractions and text:
        metadata = extractions[0]
        metadata["text"] = text
    elif extractions:
        metadata = extractions[0]
    elif text:
        metadata = {"text": text}
    elif model_id:
        metadata = {"model_id": model_id}
    else:
        metadata = {}

    code_payload = {
        "username": "extraction_service",
        "name": name,
        "description": description,
        "files": files,
        "metadata": metadata,
    }
    logger.info(f"Storing extraction to TDS for code: {code_id}")
    # patch TDS code/code
    tds_code = f"{TDS_API}/code/{code_id}"
    code_response = requests.put(tds_code, json=code_payload)
    logger.debug(f"TDS response: {code_response.text}")
    code_put_status = code_response.status_code

    return {"status": code_put_status}


def get_document_from_tds(document_id, code=False):
    tds_documents_url = f"{TDS_API}/documents/{document_id}"
    document = requests.get(tds_documents_url)
    document_json = document.json()
    if code:
        filename = document_json.get("filename")
    else:
        filename = document_json.get("file_names")[
            0
        ]  # Assumes only one file will be present for now.

    download_url = f"{TDS_API}/documents/{document_id}/download-url?document_id={document_id}&filename={filename}"
    document_download_url = requests.get(download_url)

    presigned_download = document_download_url.json().get("url")

    logger.info(presigned_download)

    downloaded_document = requests.get(document_download_url.json().get("url"))

    logger.info(f"DOCUMENT RETRIEVAL STATUS:{downloaded_document.status_code}")

    if downloaded_document.status_code != 200:
        raise Exception(
            f"Cannot download document {document_id} from TDS: {downloaded_document.text}"
        )

    return document_json, downloaded_document.content


def get_code_from_tds(code_id, code=False, dynamics_only=False):
    dynamics_off = False
    tds_codes_url = f"{TDS_API}/code/{code_id}"
    logger.info(tds_codes_url)
    code = requests.get(tds_codes_url)
    code_json = code.json()
    logger.info(code_json)

    files = code_json.get("files")
    logger.info(files)
    file_names = {}
    logger.info(files.items())
    if dynamics_only:
        for file_path, file_details in files.items():
            dynamics = file_details.get("dynamics")
            if dynamics and dynamics.get("block"):
                file_names[file_path] = dynamics["block"]

        # Fail gracefully if no dynamics are found
        if file_names == {}:
            logger.warning(
                "No dynamics found in TDS code object, turned dynamics_only off."
            )
            dynamics_only = False
            file_names = files
            dynamics_off = True
    else:
        file_names = files

    content_object = {}

    for name, blocks in file_names.items():
        # name = name.split("/")[-1]
        download_url = f"{TDS_API}/code/{code_id}/download-url?filename={name}"
        code_download_url = requests.get(download_url)

        presigned_download = code_download_url.json().get("url")

        logger.info(presigned_download)

        downloaded_code = requests.get(code_download_url.json().get("url"))

        logger.info(f"code RETRIEVAL STATUS:{downloaded_code.status_code}")

        if dynamics_only:
            all_dynamic_blocks = []
            for block in blocks:
                start_line, end_line = block.split("-")

                # Convert the extracted strings to integers, removing leading 'L'
                start_line = int(start_line[1:])
                end_line = int(end_line[1:])

                # Get the lines from the code
                code_lines = downloaded_code.content.splitlines()
                target_lines = code_lines[start_line - 1 : end_line]
                logger.info(target_lines)

                # Join the lines into a single string
                target_block = b"\n".join(target_lines)

                # Add the block to the list of blocks
                all_dynamic_blocks.append(target_block.decode("utf-8"))

            content_object[name] = all_dynamic_blocks
        else:
            content_object[name] = downloaded_code.content

    return code_json, content_object, dynamics_off


def get_dataset_from_tds(dataset_id):
    tds_datasets_url = f"{TDS_API}/datasets/{dataset_id}"

    dataset = requests.get(tds_datasets_url)
    dataset_json = dataset.json()

    logger.info(f"DATASET RESPONSE JSON: {dataset_json}")

    dataframes = []
    for filename in dataset_json.get("file_names", []):
        gen_download_url = f"{TDS_API}/datasets/{dataset_id}/download-url?dataset_id={dataset_id}&filename={filename}"
        dataset_download_url = requests.get(gen_download_url)

        logger.info(f"{dataset_download_url} {dataset_download_url.json().get('url')}")

        downloaded_dataset = requests.get(dataset_download_url.json().get("url"))

        logger.info(downloaded_dataset)

        dataset_file = io.BytesIO(downloaded_dataset.content)
        dataset_file.seek(0)

        dataframe = pandas.read_csv(dataset_file)
        dataframes.append(dataframe)

    if len(dataframes) > 1:
        final_df = pandas.merge(dataframes)
    else:
        final_df = dataframes[0]

    csv_string = final_df.to_csv(index=False)

    return dataset, final_df, csv_string


def get_model_from_tds(model_id):
    tds_model_url = f"{TDS_API}/models/{model_id}"
    model = requests.get(tds_model_url)
    return model


def set_provenance(left_id, left_type, right_id, right_type, relation_type):
    """
    Creates a provenance record in TDS. Used during code to model to associate the
    code artifact with the model AMR
    """

    provenance_payload = {
        "relation_type": relation_type,
        "left": left_id,
        "left_type": left_type,
        "right": right_id,
        "right_type": right_type,
    }

    # Create TDS provenance
    tds_provenance = f"{TDS_API}/provenance"
    logger.info(f"Storing provenance to {tds_provenance}")
    try:
        provenance_resp = requests.post(tds_provenance, json=provenance_payload)
    except Exception as e:
        logger.error(e)
        logger.info(provenance_resp.text)
        logger.info(provenance_resp.status_code)
    if provenance_resp.status_code == 200:
        logger.info(f"Stored provenance to TDS for left {left_id} and right {right_id}")
    else:
        logger.error(
            f"Storing provenance failed at {tds_provenance}: {provenance_resp.text}"
        )

    return {"status": provenance_resp.status_code}


def find_source_code(model_id):
    """
    For a given model id, finds the associated source code artifact from which it was extracted
    """

    payload = {"root_id": model_id, "root_type": "Model"}

    tds_provenance = f"{TDS_API}/provenance/search?search_type=models_from_code"
    resp = requests.post(tds_provenance, json=payload)
    logger.info(f"Provenance code lookup for model ID {model_id}: {resp.json()}")
    results = resp.json().get("result", [])
    if len(results) > 0:
        return results[0]
    else:
        return None
