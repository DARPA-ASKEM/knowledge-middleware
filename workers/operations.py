import io
import json
import os
import urllib
import sys
import requests
import pandas

from utils import put_amr_to_tds, put_artifact_to_tds

TDS_API = os.getenv("TDS_URL")
SKEMA_API = os.getenv("SKEMA_RS_URL")
UNIFIED_API = os.getenv("TA1_UNIFIED_URL")
MIT_API = os.getenv("MIT_TR_URL")


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
    unified_text_reading_url = f"{UNIFIED_API}/text-reading/integrated-text-extractions?annotate_skema={annotate_skema}&annotate_mit={annotate_mit}"
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

        extraction_json = extraction_json.get("outputs").get("data")

    except ValueError:
        return {
            "status_code": 500,
            "extraction": None,
            "artifact_id": None,
        }

    artifact_response = put_artifact_to_tds(
        bytes_obj=bytes_obj,
        name=name,
        description=description,
        filename=filename,
        extractions=extraction_json,
    )

    response = {
        "status_code": response.status_code,
        "extraction": extraction_json,
        "artifact_id": artifact_response.get("artifact_id"),
    }

    return response


def data_profiling(dataset_id, document_text):
    openai_key = os.getenv("OPENAI_API_KEY")

    tds_datasets_url = f"{TDS_API}/datasets"

    dataset = requests.get(tds_datasets_url, data={"id": dataset_id})
    dataset_json = dataset.json()

    dataframes = []
    for filename in dataset_json.get("filenames", []):
        gen_download_url = f"{TDS_API}/datasets/{dataset_id}/download-url?dataset_id={dataset_id}&filename={filename}"
        dataset_download_url = requests.get(gen_download_url)

        downloaded_dataset = requests.get(dataset_download_url)

        dataframe = pandas.read_csv(downloaded_dataset.content)
        dataframes.append(dataframe)

    final_df = pandas.merge(dataframes)

    ######################################################
    # Now we do the actual profiling!
    ######################################################

    # Here we perform our first call to the MIT service
    mit_url = MIT_API

    csv_string = final_df.to_csv()

    resp = requests.post(
        url=f"{mit_url}/annotation/link_dataset_col_to_dkg",
        params={"csv_str": csv_string, "doc": document_text, "gpt_key": openai_key},
    )
    mit_groundings = resp.json()

    # here we perform our 2nd call to the MIT service
    resp = requests.post(
        url=f"{mit_url}/annotation/upload_file_extract/?gpt_key={openai_key}",
        files={"file": csv_string},
    )
    resp.json()
    mit_annotations = {a["name"]: a for a in resp.json()}

    #######################################
    # processing the results from MIT into the format
    # expected by TDS
    #######################################

    columns = []
    for c in final_df.columns:
        annotations = mit_annotations.get(c, {}).get("text_annotations", [])
        # Skip any single empty strings that are sometimes returned and drop extra items that are sometimes included (usually the string 'class')
        groundings = {
            g[0]: g[1]
            for g in mit_groundings.get(c, None).get("dkg_groundings", None)
            if g and isinstance(g, list)
        }
        col = {
            "name": c,
            "data_type": "float",
            "description": annotations[0].strip(),
            "annotations": [],
            "metadata": {},
            "grounding": {
                "identifiers": groundings,
            },
        }
        columns.append(col)

    dataset["columns"] = columns

    dataset["metadata"] = {
        "document_textuments": [
            {
                "url": "https://github.com/reichlab/covid19-forecast-hub/blob/master/data-truth/README.md",
                "title": "README: Ground truth data for the COVID-19 Forecast Hub",
            }
        ]
    }

    resp = requests.post(f"{TDS_API}/datasets", json=dataset)
    dataset_id = resp.json()["id"]
    resp.json()
