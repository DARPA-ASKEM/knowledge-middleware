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


# def report(upload=True):
#     publish_report(gen_report(), upload)


# PIPELINE CODE
def run_km_job(url, scenario, task_name, kwargs=None):
    if kwargs is None:
        kwargs = {}
    start_time = time()
    km_response = requests.post(url, **kwargs)

    if km_response.status_code != 200:
        raise Exception(
            f"Knowledge Middleware returned {km_response.status_code} for '{task_name}' on scenario: {scenario}"
        )

    response_json = km_response.json()
    logging.info(f" {response_json}")
    # Check if RQ job is successful, if not poll for completion of job
    if response_json["status"] == "queued":
        job_id = response_json["id"]
        while True:
            sleep(3)
            job_status = requests.get(f"{KM_URL}/status/{job_id}").json()
            logging.info(job_status)
            if job_status["status"] == "finished":
                logging.info(f"{task_name} job: {job_id} - status: finished")
                return job_status, time() - start_time
            elif job_status["status"] == "failed":
                logging.error(f"{task_name} job: {job_id} - status: failed")
                return job_status, time() - start_time
    elif response_json["status"] == "finished":
        logging.info(f"{task_name} job: {job_id} - status: finished")
        return response_json, time() - start_time
    else:
        raise Exception(
            f"Knowledge Middleware returned {km_response.status_code} for '{task_name}' on scenario: {scenario}"
        )


def pdf_to_cosmos(scenario):
    task_name = "pdf to cosmos"
    url = f"{KM_URL}/pdf_to_cosmos?document_id={scenario}"

    return run_km_job(url, scenario, task_name)


def pdf_to_text(scenario):
    task_name = "pdf to text"
    url = f"{KM_URL}/pdf_extractions?document_id={scenario}"

    return run_km_job(url, scenario, task_name)


def code_to_amr(scenario):
    # Try dynamics only since code_to_amr fallsback to full if dynamics fails
    task_name = "code to AMR"
    url = f"{KM_URL}/code_to_amr?code_id={scenario}&dynamics_only=True"

    return run_km_job(url, scenario, task_name)


def profile_model(scenario, model_id, document_id):
    task_name = "profile model"
    url = f"{KM_URL}/profile_model/{model_id}?document_id={document_id}"

    return run_km_job(url, scenario, task_name)


def link_amr(scenario, model_id, document_id):
    task_name = "link AMR"
    url = f"{KM_URL}/link_amr?document_id={document_id}&model_id={model_id}"

    return run_km_job(url, scenario, task_name)


def pipeline(scenario):
    report = {}

    # TODO: Hardcoded, generate shape from scenario files.
    shape = [
        {
            "from": "pdf_to_cosmos",
            "to": "pdf_to_text",
        },
        {
            "from": "pdf_to_text",
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
    try:
        cosmos_response, execution_time = pdf_to_cosmos(scenario=scenario)
        document_id = scenario
        # cosmos_response["result"]["job_result"].pop("extraction")
        report["pdf_to_cosmos"] = cosmos_response
        report["pdf_to_cosmos"]["time"] = execution_time

        text_response, execution_time = pdf_to_text(scenario=scenario)
        # text_response["result"]["job_result"].pop("extraction")
        report["pdf_to_text"] = text_response
        report["pdf_to_text"]["time"] = execution_time

        amr_response, execution_time = code_to_amr(scenario=scenario)
        if amr_response["result"]["job_result"]:
            model_id = amr_response["result"]["job_result"]["tds_model_id"]
        else:
            model_id = None
        report["code_to_amr"] = amr_response
        report["code_to_amr"]["time"] = execution_time

        if model_id is None:
            raise Exception(
                f"Model was not generated for scenario: {scenario}, amr creation response: {amr_response}"
            )
        profile_response, execution_time = profile_model(
            scenario=scenario, model_id=model_id, document_id=document_id
        )
        report["profile_model"] = profile_response
        report["profile_model"]["time"] = execution_time

        link_response, execution_time = link_amr(
            scenario=scenario, model_id=model_id, document_id=document_id
        )
        report["link_amr"] = link_response
        report["link_amr"]["time"] = execution_time

        pipeline_report = {
            "success": True,
            "steps": report,
            "shape": shape,
            "accuracy": {},
        }

        return {scenario: pipeline_report}
    except Exception as e:
        logging.error(f"Pipeline did not complete on scenario: {scenario}, error: {e}")
        pipeline_report = {
            "success": False,
            "steps": report,
            "shape": shape,
            "accuracy": {},
        }
        return {scenario: pipeline_report}


# MAIN DECLARATION
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
