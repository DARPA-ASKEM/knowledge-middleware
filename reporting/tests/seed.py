from glob import glob
import json
import os

import requests

TDS_URL = os.environ.get("TDS_URL", "http://data-service:8000")

# TODO: Populate TDS

# EXAMPLE [TODO: DELETE ]
# model_configs = glob("./data/models/*.json")
# for config_path in model_configs:
#     config = json.load(open(config_path, 'rb'))
#     model = config["configuration"]
#     model_response = requests.post(TDS_URL + "/models", json=model, headers={
#         "Content-Type": "application/json"
#     })
#     if model_response.status_code >= 300:
#         raise Exception(f"Failed to POST model ({model_response.status_code}): {config['id']}")
#     config["model_id"] = model_response.json()["id"]
#     config_response = requests.post(TDS_URL + "/model_configurations", json=config,
#         headers= {
#             "Content-Type": "application/json"
#         }    
#     )

    
#     if config_response.status_code >= 300:
#         raise Exception(f"Failed to POST config ({config_response.status_code}): {config['id']}")

