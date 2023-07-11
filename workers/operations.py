import io
import json
import os
import urllib
import sys
import requests

from utils import put_amr_to_tds

TDS_API = os.getenv("TDS_URL")
SKEMA_API = os.getenv("SKEMA_URL")

# Worker jobs for TA1 services
def put_mathml_to_skema(*args, **kwargs):

    # Get vars
    mathml = kwargs.get("mathml")
    model = kwargs.get("model")

    # PUT the mathml to the skema endpoint.
    skema_mathml_url = SKEMA_API + "/mathml/amr"

    headers = {
        "Content-Type": "application/json"
    }

    put_payload = {
        "mathml": mathml,
        "model": model
    }

    amr_response = requests.put(skema_mathml_url, data=json.dumps(put_payload, default=str), headers=headers)
    amr_json = amr_response.json()

    tds_responses = put_amr_to_tds(amr_json)

    response = {
        "status_code": amr_response.status_code,
        "amr": amr_json,
        "tds_model_id": tds_responses.get("model_id"),
        "tds_configuration_id": tds_responses.get("configuration_id")
    }

    return response