import json
import os
import requests
import sys

TDS_API = os.getenv("TDS_URL")


def put_amr_to_tds(amr_payload):
    # Expects json amr payload and puts it to TDS models and model-configurations, returning an ID.

    headers = {"Content-Type": "application/json"}

    print(amr_payload)

    # Create TDS model
    tds_models = TDS_API + "/models"
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

    return {"model_id": model_id, "configuration_id": config_id}


def put_artifact_extraction_to_tds(
    name, description, filename, extractions
):  # TODO change to get artifact from TDS via filename and artifact id maybe
    headers = {"Content-Type": "application/json"}

    artifact_payload = {
        "username": "extraction_service",
        "name": name,
        "description": description,
        "file_names": [filename],
        "metadata": extractions[0],
    }

    # Create TDS artifact
    tds_artifact = TDS_API + "/artifacts"
    artifact_response = requests.put(
        tds_artifact, data=json.dumps(artifact_payload, default=str), headers=headers
    )

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

    print(presigned_download)
    sys.stdout.flush()

    downloaded_artifact = requests.get(artifact_download_url.json().get("url"))

    print(f"ARTIFACT RETRIEVAL STATUS:{downloaded_artifact.status_code}")
    sys.stdout.flush()

    return artifact_json, downloaded_artifact.content
