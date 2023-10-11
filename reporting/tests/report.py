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


SKEMA_RS_URL = os.environ.get("SKEMA_RS_URL ")
TA1_UNIFIED_URL = os.environ.get("TA1_UNIFIED_URL ")
COSMOS_URL = os.environ.get("COSMOS_URL ")
MIT_TR_URL = os.environ.get("MIT_TR_URL ")

TDS_URL = os.environ.get("TDS_URL", "http://data-service:8000")
KM_URL = os.environ.get(
    "KNOWLEDGE_MIDDLEWARE_URL", "http://knowledge-middleware-api:8000"
)
BUCKET = os.environ.get("BUCKET", None)
UPLOAD = os.environ.get("UPLOAD", "FALSE").lower() == "true"


def run_km_job(url, scenario, task_name, kwargs=None):
    if kwargs is None:
        kwargs = {}
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
                return job_status
            elif job_status["status"] == "failed":
                raise Exception(
                    f"Knowledge Middleware job {task_name} - {job_id} failed"
                )
    elif response_json["status"] == "finished":
        logging.info(f"{task_name} job: {job_id} - status: finished")
        return response_json
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
    try:
        cosmos_response = pdf_to_cosmos(scenario=scenario)
        document_id = scenario
        cosmos_response["result"]["job_result"].pop("extraction")
        # report_object = {"name": "pdf_to_cosmos", "result": cosmos_response"}
        report["pdf_to_cosmos"] = cosmos_response

        text_response = pdf_to_text(scenario=scenario)
        text_response["result"]["job_result"].pop("extraction")
        report["pdf_to_text"] = text_response

        amr_response = code_to_amr(scenario=scenario)
        model_id = amr_response["model_id"]
        report["code_to_amr"] = amr_response

        profile_response = profile_model(
            scenario=scenario, model_id=model_id, document_id=document_id
        )
        report["profile_model"] = profile_response

        link_response = link_amr(
            scenario=scenario, model_id=model_id, document_id=document_id
        )
        report["link_amr"] = link_response

        return report
    except:
        logging.error(f"Pipeline did not complete on scenario: {scenario}")
        return report


if __name__ == "__main__":
    for scenario in os.listdir("./scenarios"):
        logging.info(f"Pipeline running on: {scenario}")
        report = pipeline(scenario)

        logging.info(f"Pipeline report: {report}")


# QUESTION: Are we running the whole workflow here?
# def eval_integration():  # TODO: Specify more specific args
#     start_time = time()
#     is_success = False

#     # TODO: Eval code

#     return {"Integration Status": is_success, "Execution Time": time() - start_time}


# def handle_bad_versioning(func):
#     try:
#         return func()
#     except requests.exceptions.ConnectionError:
#         return "UNAVAILABLE (CANNOT CONNECT)"
#     except KeyError:
#         return "UNAVAILABLE (NO ENDPOINT)"


# def gen_report():
#     report = {
#         "scenarios": {},
#         "services": {
#             "TA1_UNIFIED_URL": {
#                 "source": TA1_UNIFIED_URL,
#                 "version": handle_bad_versioning(
#                     lambda: requests.get(
#                         f"{settings.TA1_UNIFIED_URL}/version"
#                     ).content.decode()
#                 ),
#             },
#             "MIT_TR_URL": {
#                 "source": MIT_TR_URL,
#                 "version": handle_bad_versioning(
#                     lambda: requests.get(
#                         f"{settings.MIT_TR_URL}/debugging/get_sha"
#                     ).json()["mitaskem_commit_sha"]
#                 ),
#             },
#             "COSMOS_URL": {
#                 "source": COSMOS_URL,
#                 "version": handle_bad_versioning(
#                     lambda: requests.get(f"{settings.COSMOS_URL}/version_info").json()[
#                         "git_hash"
#                     ]
#                 ),
#             },
#             "SKEMA_RS_URL": {"source": settings.SKEMA_RS_URL, "version": "UNAVAILABLE"},
#         },
#     }

#     scenarios = {name: {} for name in os.listdir("scenarios")}
#     # for scenario in scenarios:
#     #     # TODO: Grab resources properly
#     #     # TODO: Call `eval_integration`
#     return report


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
