import json
import os
import requests
import sys

TDS_API = os.getenv("TDS_URL")

def put_amr_to_tds(amr_payload):
    # Expects json amr payload and puts it to TDS models and model-configurations, returning an ID.

    headers = {
        "Content-Type": "application/json"
    }

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
        "configuration": json.loads(json.dumps(amr_payload))
    }
    config_response = requests.post(tds_model_configurations, data=json.dumps(configuration_payload, default=str), headers=headers)

    config_id = config_response.json().get("id")

    return {
        "model_id": model_id,
        "configuration_id": config_id
    }