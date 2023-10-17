import os
import json
import logging
from time import sleep, time
from datetime import datetime
from collections import defaultdict

import boto3
import requests

from utils import post_to_km_endpoint

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


SKEMA_RS_URL = os.environ.get("SKEMA_RS_URL")
TA1_UNIFIED_URL = os.environ.get("TA1_UNIFIED_URL")
COSMOS_URL = os.environ.get("COSMOS_URL")
MIT_TR_URL = os.environ.get("MIT_TR_URL")

TDS_URL = os.environ.get("TDS_URL", "http://data-service:8000")
KM_URL = os.environ.get(
    "KNOWLEDGE_MIDDLEWARE_URL", "http://knowledge-middleware-api:8000"
)
BUCKET = os.environ.get("BUCKET", None)
UPLOAD = os.environ.get("UPLOAD", "FALSE").lower() == "true"


# REPORT GENERATION
def handle_bad_versioning(func):
    try:
        return func()
    except requests.exceptions.ConnectionError:
        return "UNAVAILABLE (CANNOT CONNECT)"
    except KeyError:
        return "UNAVAILABLE (NO ENDPOINT)"


def gen_report(scenarios_reports):
    report = {
        "scenarios": scenarios_reports,
        "services": {
            "TA1_UNIFIED_URL": {
                "source": TA1_UNIFIED_URL,
                "version": handle_bad_versioning(
                    lambda: requests.get(f"{TA1_UNIFIED_URL}/version").content.decode()
                ),
            },
            # Currently unneeded since the Unified service defines the other services used.
            # "MIT_TR_URL": {
            #     "source": MIT_TR_URL,
            #     "version": handle_bad_versioning(
            #         lambda: requests.get(f"{MIT_TR_URL}/debugging/get_sha").json()[
            #             "mitaskem_commit_sha"
            #         ]
            #     ),
            # },
            # "COSMOS_URL": {
            #     "source": COSMOS_URL,
            #     "version": handle_bad_versioning(
            #         lambda: requests.get(f"{COSMOS_URL}/version_info").json()[
            #             "git_hash"
            #         ]
            #     ),
            # },
            # "SKEMA_RS_URL": {"source": SKEMA_RS_URL, "version": "UNAVAILABLE"},
        },
    }
    return report


def publish_report(report, upload):
    logging.info("Publishing report")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.json"
    fullpath = os.path.join("reports", filename)
    os.makedirs("reports", exist_ok=True)
    with open(fullpath, "w") as file:
        json.dump(report, file, indent=2)

    if upload and BUCKET is not None:
        logging.info(f"Uploading report to '{BUCKET}'")
        s3 = boto3.client("s3")
        full_handle = os.path.join("ta1", filename)
        s3.upload_file(fullpath, BUCKET, full_handle)

    elif upload and BUCKET is None:
        logging.error("NO BUCKET WAS PROVIDED. CANNOT UPLOAD")

    if not upload or BUCKET is None:
        logging.info(f"{fullpath}:")
        logging.info(open(fullpath, "r").read())


# PIPELINE CODE
def run_km_job(url, scenario, task_name):
    start_time = time()
    km_response = requests.post(url)

    if km_response.status_code != 200:
        raise Exception(
            f"Knowledge Middleware returned {km_response.status_code} for '{task_name}' on scenario: {scenario}"
        )

    response_json = km_response.json()
    job_id = response_json["id"]
    result = None
    while True:
        sleep(1)
        result = requests.get(f"{KM_URL}/status/{job_id}").json()
        logging.info(result)
        if result["status"] == "finished":
            success = True
            logging.info(f"{task_name} job: {job_id} - status: finished")
            break
        elif result["status"] == "failed":
            success = False
            logging.error(f"{task_name} job: {job_id} - status: failed")
            break
    

    execution_time = time() - start_time
    result.update({
        "time" : execution_time,
        "accuracy" : {},
        "success" : success
    })
    return result


def standard_flow(scenario):
    document_id = scenario
    def do_task(url, task):
        return (task, run_km_job(url, scenario, task))

    # STEP 1: PDF EXTRACTION
    yield do_task(
        url = f"{KM_URL}/pdf_extraction?document_id={scenario}",
        task = "pdf_extraction"
    )
    
    # STEP 2: VARIABLE EXTRACTION
    yield do_task(
        url = f"{KM_URL}/variable_extractions?document_id={scenario}",
        task = "variable_extraction"
    )

    # STEP 3: CODE TO AMR
    # Try dynamics only since code_to_amr fallsback to full if dynamics fails
    (task, result) = do_task(
        url = f"{KM_URL}/code_to_amr?code_id={scenario}&dynamics_only=True",
        task = "code_to_amr"
    )
    if result["success"]:
        model_id = result["result"]["job_result"]["tds_model_id"]
    else:
        logging.error(
            f"Model was not generated for scenario: {scenario}, amr creation response: {result}"
        )
    yield task, result

    # STEP 4: PROFILE AMR
    yield do_task(
        url = f"{KM_URL}/profile_model/{model_id}?document_id={document_id}",
        task = "profile_model"
    )
    
    # STEP 5: LINK AMR
    yield do_task(
        url = f"{KM_URL}/link_amr?document_id={document_id}&model_id={model_id}",
        task = "link_amr"
    )


def pipeline(scenario):
    # TODO: Hardcoded, generate shape from scenario files.
    shape = [
        {
            "from": "pdf_extraction",
            "to": "variable_extraction",
        },
        {
            "from": "variable_extraction",
            "to": "profile_model",
        },
        {
            "from": "code_to_amr",
            "to": "profile_model",
        },
        {
            "from": "profile_model",
            "to": "link_amr",
        },
    ]
    report = {}
    success = True
    for (task, result) in standard_flow(scenario):
        report[task] = result
        if not result["success"]:
            success = False
            logging.error(f"Pipeline did not complete on scenario: {scenario}, error: {result['result']['job_error']}")
            break

    description_path = f"./scenarios/{scenario}/description.txt"
    if os.path.exists(description_path):
        description = open(description_path).read()
    else:
        description = ""
    pipeline_report = {
        "success": success,
        "description": description,
        "steps": report,
        "shape": shape,
        "accuracy": {},
    }
    return {scenario: pipeline_report}


if __name__ == "__main__":
    reports = []
    for scenario in os.listdir("./scenarios"):
        logging.info(f"Pipeline running on: {scenario}")
        report = pipeline(scenario)

        logging.info(f"{scenario} Pipeline report: {report}")

        reports.append(report)

    # Merge all objects in reports into one object
    merged_report = {}
    for report in reports:
        for key, value in report.items():
            merged_report[key] = value

    logging.info(f"Merged report: {merged_report}")

    final_report = gen_report(merged_report)

    logging.info(f"Final report: {final_report}")

    publish_report(final_report, UPLOAD)
