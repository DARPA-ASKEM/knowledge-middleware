import os
import json
import logging
from time import sleep, time
from datetime import datetime
from collections import defaultdict

import boto3
import requests

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


SKEMA_RS_URL = os.environ.get("SKEMA_RS_URL ")
TA1_UNIFIED_URL = os.environ.get("TA1_UNIFIED_URL ")
COSMOS_URL = os.environ.get("COSMOS_URL ")
MIT_TR_URL = os.environ.get("MIT_TR_URL ")

TDS_URL = os.environ.get("TDS_URL", "http://data-service:8000")
PYCIEMSS_URL = os.environ.get("KNOWLEDGE_MIDDLEWARE_URL", "http://knowledge-middleware-api:8000")
BUCKET = os.environ.get("BUCKET", None)
UPLOAD = os.environ.get("UPLOAD", "FALSE").lower() == "true"


# QUESTION: Are we running the whole workflow here?
def eval_integration(): # TODO: Specify more specific args
    start_time = time()
    is_success = False

    # TODO: Eval code
    
    return {
        "Integration Status": is_success,
        "Execution Time": time() - start_time
    }


def handle_bad_versioning(func):
    try:
        return func()
    except requests.exceptions.ConnectionError:
        return "UNAVAILABLE (CANNOT CONNECT)"
    except KeyError:
        return "UNAVAILABLE (NO ENDPOINT)"


def gen_report():
    report = {
        "scenarios": {},
        "services": {
            "TA1_UNIFIED_URL":{
              "source": TA1_UNIFIED_URL,  
              "version": handle_bad_versioning(lambda: requests.get(f"{settings.TA1_UNIFIED_URL}/version").content.decode())
            },
            "MIT_TR_URL":{
              "source": MIT_TR_URL,  
              "version": handle_bad_versioning(lambda: requests.get(f"{settings.MIT_TR_URL}/debugging/get_sha").json()["mitaskem_commit_sha"])
            },
            "COSMOS_URL":{
              "source": COSMOS_URL,  
              "version": handle_bad_versioning(lambda: requests.get(f"{settings.COSMOS_URL}/version_info").json()["git_hash"])
            },
            "SKEMA_RS_URL":{
              "source": settings.SKEMA_RS_URL,  
              "version": "UNAVAILABLE"
            },
        }
    }

    scenarios = {name: {} for name in os.listdir("scenarios")}
    for scenario in scenarios:
        # TODO: Grab resources properly
        # TODO: Call `eval_integration`
    return report


def publish_report(report, upload):
    logging.info("Publishing report")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
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


def report(upload=True):
    publish_report(gen_report(), upload)


if __name__ == "__main__":
    report(UPLOAD)