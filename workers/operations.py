import io
import json
import os
import urllib
import sys
import requests

from utils import put_amr_to_tds, put_artifact_to_tds

TDS_API = os.getenv("TDS_URL")
SKEMA_API = os.getenv("SKEMA_RS_URL")
UNIFIED_API = os.getenv("TA1_UNIFIED_URL")


# Worker jobs for TA1 services
def put_mathml_to_skema(*args, **kwargs):
    # Get vars
    mathml = kwargs.get("mathml")
    model = kwargs.get("model")

    # PUT the mathml to the skema endpoint.
    skema_mathml_url = SKEMA_API + "/mathml/amr"

    headers = {"Content-Type": "application/json"}

    put_payload = {"mathml": mathml, "model": model}

    amr_response = requests.put(
        skema_mathml_url, data=json.dumps(put_payload, default=str), headers=headers
    )
    amr_json = amr_response.json()

    tds_responses = put_amr_to_tds(amr_json)

    response = {
        "status_code": amr_response.status_code,
        "amr": amr_json,
        "tds_model_id": tds_responses.get("model_id"),
        "tds_configuration_id": tds_responses.get("configuration_id"),
    }

    return response


def pdf_extractions(*args, **kwargs):
    # Get options
    text_content = kwargs.get("text_content")
    annotate_skema = kwargs.get("annotate_skema")
    annotate_mit = kwargs.get("annotate_mit")
    bytes_obj = kwargs.get("bytes_obj")
    filename = kwargs.get("filename")
    name = kwargs.get("name")
    description = kwargs.get("description")

    # Try to feed text to the unified service
    unified_text_reading_url = (
        UNIFIED_API
    ) = f"/text-reading/integrated-text-extractions?annotate_skema={annotate_skema}&annotate_mit={annotate_mit}"
    headers = {"Content-Type": "application/json"}
    put_payload = {"texts": [text_content]}

    try:
        response = requests.post(
            unified_text_reading_url,
            data=json.dumps(put_payload, default=str),
            headers=headers,
        )
        extraction_json = response.json()

        if extraction_json.get("outputs", {"data": None}).get("data", None) is None:
            raise ValueError

    except ValueError:
        # Extractions were null from unified service, try integrated service directly.
        text_reading_url = (
            os.getenv("INTEGRATED_TR_URL")
            + f"/integrated_text_extractions/?annotate_skema={annotate_skema}&annotate_mit={annotate_mit}"
        )

        response = requests.post(
            text_reading_url, data=json.dumps(put_payload, default=str), headers=headers
        )
        extraction_json = response.json()

    artifact_response = put_artifact_to_tds(
        bytes_obj=bytes_obj,
        name=name,
        description=description,
        filename=filename,
        extractions=extraction_json,
    )

    response = response = {
        "status_code": response.status_code,
        "extraction": extraction_json,
        "artifact_id": artifact_response.get("artifact_id"),
    }

    return response
