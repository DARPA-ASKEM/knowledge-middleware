import io
import json
import os
import urllib
import sys
import requests
import pandas

from utils import (
    put_amr_to_tds,
    put_artifact_extraction_to_tds,
    get_artifact_from_tds,
    get_dataset_from_tds,
)

TDS_API = os.getenv("TDS_URL")
SKEMA_API = os.getenv("SKEMA_RS_URL")
UNIFIED_API = os.getenv("TA1_UNIFIED_URL")
MIT_API = os.getenv("MIT_TR_URL")

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


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

    if amr_response.status_code == 200:
        amr_json = amr_response.json()

        tds_responses = put_amr_to_tds(amr_json)

        response = {
            "status_code": amr_response.status_code,
            "amr": amr_json,
            "tds_model_id": tds_responses.get("model_id"),
            "tds_configuration_id": tds_responses.get("configuration_id"),
            "error": None,
        }

        return response
    else:
        response = {
            "status_code": amr_response.status_code,
            "amr": None,
            "tds_model_id": None,
            "tds_configuration_id": None,
            "error": amr_response.text,
        }

        return response


def pdf_extractions(*args, **kwargs):
    # Get options
    artifact_id = kwargs.get("artifact_id")
    annotate_skema = kwargs.get("annotate_skema")
    annotate_mit = kwargs.get("annotate_mit")
    name = kwargs.get("name")
    description = kwargs.get("description")

    artifact_json, downloaded_artifact = get_artifact_from_tds(
        artifact_id=artifact_id
    )  # Assumes  downloaded artifact is PDF, doesn't type check
    filename = artifact_json.get("file_names")[0]

    # Try to feed text to the unified service
    unified_text_reading_url = f"{UNIFIED_API}/text-reading/integrated-pdf-extractions?annotate_skema={annotate_skema}&annotate_mit={annotate_mit}"
    headers = {"Content-Type": "application/json"}
    put_payload = {
        "pdfs": [
            (
                "extractions.json",
                downloaded_artifact,
                "application/json",
            )
        ]
    }

    try:
        response = requests.post(
            unified_text_reading_url,
            files=put_payload,
            headers=headers,
        )
        extraction_json = response.json()

        if extraction_json.get("outputs", {"data": None}).get("data", None) is None:
            raise ValueError

        extraction_json = extraction_json.get("outputs").get("data")

    except ValueError:
        return {
            "status_code": 500,
            "extraction": None,
            "artifact_id": None,
            "error": "Extractions did not complete, extractions values were null.",
        }

    artifact_response = put_artifact_extraction_to_tds(
        name=name if name is not None else artifact_json.get("name"),
        description=description
        if description is not None
        else artifact_json.get("description"),
        filename=filename,
        extractions=extraction_json,
    )

    if artifact_response.get("status") == 200:
        response = {
            "extraction_status_code": response.status_code,
            "extraction": extraction_json,
            "tds_status_code": artifact_response.get("status"),
            "error": None,
        }
    else:
        response = {
            "extraction_status_code": response.status_code,
            "extraction": extraction_json,
            "tds_status_code": artifact_response.get("status"),
            "error": "PUT extraction metadata to TDS failed, please check TDS api logs.",
        }

    return response


def dataset_profiling(*args, **kwargs):
    openai_key = os.getenv("OPENAI_API_KEY")
    dataset_id = kwargs.get("dataset_id")

    dataset_response, dataset_dataframe, dataset_csv_string = get_dataset_from_tds(
        dataset_id
    )

    dataset_json = dataset_response.json()

    # here we perform our 2nd call to the MIT service
    resp = requests.post(
        url=f"{MIT_API}/annotation/upload_file_extract/?gpt_key={openai_key}",
        files={"file": dataset_csv_string},
    )
    resp.json()
    mit_annotations = {a["name"]: a for a in resp.json()}

    print(f"MIT ANNOTATIONS: {mit_annotations}")
    sys.stdout.flush()

    columns = []
    for c in dataset_dataframe.columns:
        annotations = mit_annotations.get(c, {}).get("text_annotations", [])
        col = {
            "name": c,
            "data_type": "float",
            "description": annotations[0].strip(),
            "annotations": [],
            "metadata": {},
        }
        columns.append(col)

    dataset_json["columns"] = columns

    resp = requests.put(f"{TDS_API}/datasets/{dataset_id}", json=dataset_json)
    dataset_id = resp.json()["id"]

    return resp.json()


def dataset_profiling_with_document(*args, **kwargs):
    openai_key = os.getenv("OPENAI_API_KEY")

    dataset_id = kwargs.get("dataset_id")
    artifact_id = kwargs.get("artifact_id")

    artifact_json, downloaded_artifact = get_artifact_from_tds(artifact_id=artifact_id)

    dataset_response, dataset_dataframe, dataset_csv_string = get_dataset_from_tds(
        dataset_id
    )
    dataset_json = dataset_response.json()

    resp = requests.post(
        url=f"{MIT_API}/annotation/link_dataset_col_to_dkg",
        params={
            "csv_str": dataset_csv_string,
            "doc": downloaded_artifact,
            "gpt_key": openai_key,
        },
    )
    mit_groundings = resp.json()

    #######################################
    # processing the results from MIT into the format
    # expected by TDS
    #######################################

    columns = []
    for c in dataset_dataframe.columns:
        # Skip any single empty strings that are sometimes returned and drop extra items that are sometimes included (usually the string 'class')
        groundings = {
            g[0]: g[1]
            for g in mit_groundings.get(c, None).get("dkg_groundings", None)
            if g and isinstance(g, list)
        }
        col = {
            "name": c,
            "data_type": "float",
            "description": "",
            "annotations": [],
            "metadata": {},
            "grounding": {
                "identifiers": groundings,
            },
        }
        columns.append(col)

    dataset_json["columns"] = columns

    resp = requests.put(f"{TDS_API}/datasets/{dataset_id}", json=dataset_json)
    dataset_id = resp.json()["id"]

    return resp.json()


def link_amr(*args, **kwargs):
    artifact_id = kwargs.get("artifact_id")
    model_id = kwargs.get("model_id")

    artifact_json, downloaded_artifact = get_artifact_from_tds(artifact_id=artifact_id)

    tds_models_url = f"{TDS_API}/models"

    model = requests.get(tds_models_url, data={"model_id": model_id})
    model_json = model.json()

    model_amr = model_json.get("model")

    files = {
        "amr_file": (
            "amr.json",
            io.BytesIO(json.dumps(model_amr, ensure_ascii=False).encode("utf-8")),
            "application/json",
        ),
        "text_extractions_file": (
            "extractions.json",
            downloaded_artifact,
            "application/json",
        ),
    }

    params = {"amr_type": "petrinet"}

    skema_amr_linking_url = f"{UNIFIED_API}/metal/link_amr"

    response = requests.post(skema_amr_linking_url, files=files, params=params)

    if response.status_code == 200:
        enriched_amr = response.json()

        model_json["model"] = enriched_amr
        model_id = model_json.get("id")

        new_model_payload = model_json

        update_response = requests.put(
            f"{tds_models_url}/{model_id}", data=new_model_payload
        )

        return {
            "status": update_response.status_code,
            "message": "Model enriched and updated in TDS",
        }
