import io
import json
import os
import sys

import pandas
import requests

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # default to INFO if not set

import logging

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

TDS_API = os.getenv("TDS_URL")


def put_amr_to_tds(amr_payload, name=None, description=None):
    # Expects json amr payload and puts it to TDS models and model-configurations, returning an ID.

    headers = {"Content-Type": "application/json"}

    if name:
        amr_payload["name"] = name
    if description:
        amr_payload["description"] = description

    logger.debug(amr_payload)

    # Create TDS model
    tds_models = f"{TDS_API}/models"
    model_response = requests.post(tds_models, json=amr_payload, headers=headers)

    model_id = model_response.json().get("id")

    # Create TDS model configuration
    tds_model_configurations = TDS_API + "/model_configurations"
    configuration_payload = {
        "model_id": model_id,
        "name": amr_payload.get("name"),
        "description": amr_payload.get("description"),
        "model_version": amr_payload.get("model_version"),
        "calibrated": False,
        "configuration": json.loads(json.dumps(amr_payload)),
    }
    config_response = requests.post(
        tds_model_configurations,
        data=json.dumps(configuration_payload, default=str),
        headers=headers,
    )

    config_id = config_response.json().get("id")

    logger.info(f"Created model in TDS with id {model_id}")
    logger.info(f"Created model config in TDS with id {config_id}")
    return {"model_id": model_id, "configuration_id": config_id}


def put_artifact_extraction_to_tds(
    artifact_id, name, description, filename, extractions=None, text=None, model_id=None
):
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

    artifact_payload = {
        "username": "extraction_service",
        "name": name,
        "description": description,
        "file_names": [filename],
        "metadata": metadata,
    }
    logger.info(f"Storing extraction to TDS for artifact: {artifact_id}")
    # Create TDS artifact
    tds_artifact = f"{TDS_API}/artifacts/{artifact_id}"
    artifact_response = requests.put(tds_artifact, json=artifact_payload)
    logger.debug(f"TDS response: {artifact_response.text}")
    artifact_put_status = artifact_response.status_code

    return {"status": artifact_put_status}


def get_artifact_from_tds(artifact_id):
    tds_artifacts_url = f"{TDS_API}/artifacts/{artifact_id}"

    artifact = requests.get(tds_artifacts_url)
    artifact_json = artifact.json()

    filename = artifact_json.get("file_names")[
        0
    ]  # Assumes only one file will be present for now.

    download_url = f"{TDS_API}/artifacts/{artifact_id}/download-url?artifact_id={artifact_id}&filename={filename}"
    artifact_download_url = requests.get(download_url)

    presigned_download = artifact_download_url.json().get("url")

    logger.info(presigned_download)

    downloaded_artifact = requests.get(artifact_download_url.json().get("url"))

    logger.info(f"ARTIFACT RETRIEVAL STATUS:{downloaded_artifact.status_code}")

    return artifact_json, downloaded_artifact.content


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
