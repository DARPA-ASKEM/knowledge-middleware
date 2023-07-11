import io
import json
import os
import urllib
import sys

import requests

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

    response = {
        "status_code": amr_response.status_code,
        "amr": amr_response.json()
    }

    return response