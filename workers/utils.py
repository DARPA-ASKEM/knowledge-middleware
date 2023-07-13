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


def put_artifact_to_tds(
    bytes_obj, name, description, filename, extractions
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
    artifact_response = requests.post(
        tds_artifact, data=json.dumps(artifact_payload, default=str), headers=headers
    )

    artifact_id = artifact_response.json().get("id")

    # Get presigned URL
    tds_presign_url = (
        TDS_API + f"/artifacts/{artifact_id}/upload-url?filename={filename}"
    )
    tds_presign_response = requests.get(tds_presign_url)
    presigned_url = tds_presign_response.json().get("url")

    upload_resp = requests.put(presigned_url, data=bytes_obj)

    if upload_resp.status_code == 200:
        print("File upload completed")

    return {"artifact_id": artifact_id}
