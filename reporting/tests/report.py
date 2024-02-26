import os
import json
import logging
from time import sleep, time
from datetime import datetime
from collections import defaultdict
from lib.auth import auth_session
import sys

import boto3
import requests

from utils import post_to_km_endpoint

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


TA1_UNIFIED_URL = os.environ.get("TA1_UNIFIED_URL")
COSMOS_URL = os.environ.get("COSMOS_URL")
MIT_TR_URL = os.environ.get("MIT_TR_URL")

TDS_URL = os.environ.get("TDS_URL", "http://data-service:8000")
KM_URL = os.environ.get(
    "KNOWLEDGE_MIDDLEWARE_URL", "http://knowledge-middleware-api:8000"
)
BUCKET = os.environ.get("BUCKET", None)
UPLOAD = os.environ.get("UPLOAD", "FALSE").lower() == "true"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def add_asset(resource_id, resource_type, project_id):
    resp = auth_session().post(f"{TDS_URL}/projects/{project_id}/assets/{resource_type}/{resource_id}")
    return resp.json()

def add_provenance(left_id, left_type, right_id, right_type, relation_type):
    payload = {"left": left_id,
               "left_type": left_type,
               "right": right_id,
               "right_type": right_type,
               "relation_type": relation_type}
    resp = auth_session().post(f"{TDS_URL}/provenance", json=payload)
    logging.info(f"Created provenance for {left_type} extracted from {right_type}")
    logging.info(f"Created provenance ID: {resp.json()['id']}")
    return resp.json()

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
            "SKEMA": {
                "source": TA1_UNIFIED_URL,
                "version": handle_bad_versioning(
                    lambda: requests.get(f"{TA1_UNIFIED_URL}/version").content.decode()
                ),
            },
            "MIT": {
                "source": MIT_TR_URL,
                "version": handle_bad_versioning(
                    lambda: requests.get(f"{MIT_TR_URL}/debugging/get_sha").json()[
                        "mitaskem_commit_sha"
                    ]
                ),
            },
            "COSMOS": {
                "source": COSMOS_URL,
                "version": handle_bad_versioning(
                    lambda: requests.get(f"{COSMOS_URL}/version_info").json()[
                        "git_hash"
                    ]
                ),
            },
        },
    }
    return report


def publish_report(report, upload):
    logging.info("Publishing report")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.json"
    fullpath = os.path.join("/outputs/ta1/", filename)
    os.makedirs("/outputs/ta1", exist_ok=True)
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
def run_km_job(url, scenario, task_name, kwargs={}):
    start_time = time()
    km_response = requests.post(url, **kwargs)

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
    result.update({"time": execution_time, "accuracy": None, "success": success})
    return result


def non_applicable_run(task_name):
    return (task_name, {"success": "N/A", "time": None, "accuracy": None})


def upstream_failure(task_name):
    return (task_name, {"success": None, "time": None, "accuracy": None})


def standard_flow(scenario, _id):
    document_id = _id
    code_id = _id
    dataset_id = _id
    model_id = _id
    model_exists = False

    def do_task(url, task, kwargs={}):
        return (task, run_km_job(url, scenario, task, kwargs))

    # STEP 1: PDF EXTRACTION
    if os.path.exists(f"scenarios/{scenario}/paper.pdf"):
        logging.info(f"PDF exists for scenario {scenario}")

        (task, result) = do_task(
            url=f"{KM_URL}/pdf_extraction?document_id={document_id}&force_run=true",
            task="pdf_extraction",
        )

        global cosmos_extraction_json
        cosmos_extraction_json = result["result"]["job_result"]["extraction"]

        # EVAL STEP 1
        ground_truth_path = (
            f"scenarios/{scenario}/ground_truth/cosmos_ground_truth.json"
        )
        if os.path.exists(ground_truth_path):
            try:
                logging.info(f"Accuracy for {scenario}:{task}")
                cosmos_job_id = result["result"]["job_result"]["cosmos_job_id"]
                with open(ground_truth_path) as file:
                    truth = file.read()
                    ground_truth_json = json.loads(truth)
                    eval = requests.post(
                        f"{COSMOS_URL}/healthcheck/evaluate/{cosmos_job_id}",
                        json=ground_truth_json,
                    )
                    if eval.status_code < 300:
                        evaluation = eval.json()[0]
                        # Extract metrics that COSMOS team said were most important
                        evaluation_stats = {
                            "document_overlap_percent": evaluation[
                                "document_overlap_percent"
                            ],
                            "document_expected_count": evaluation[
                                "document_expected_count"
                            ],
                            "document_cosmos_count": evaluation[
                                "document_cosmos_count"
                            ],
                        }
                        result["accuracy"] = evaluation_stats
                    else:
                        result["accuracy"] = {"status_code": eval.status_code}
            except Exception as e:
                logging.error(f"Cosmos Accuracy Error: {e}")
        else:
            logging.info(f"No ground truth exists for: {scenario}:{task}")
            result["accuracy"] = None
        yield task, result
    else:
        yield non_applicable_run("pdf_extraction")

    # STEP 2: VARIABLE EXTRACTION
    # Check TDS document to see if it has non null text
    if os.path.exists(f"scenarios/{scenario}/domain.txt"):
        domain = open(f"scenarios/{scenario}/domain.txt").read()
        logging.info(f"Domain found: {domain}")
        url = f"{KM_URL}/variable_extractions?document_id={document_id}&domain={domain}"
    else:
        url = f"{KM_URL}/variable_extractions?document_id={document_id}"
    document_response = auth_session().get(f"{TDS_URL}/document-asset/{document_id}")
    if document_response.status_code > 300:
        yield non_applicable_run("variable_extraction")
    else:
        document = document_response.json()
        # PDF extraction failed, mark upstream failure
        if document["text"] is None:
            yield upstream_failure("variable_extraction")
        else:
            (task, result) = do_task(
                url=f"{KM_URL}/variable_extractions?document_id={document_id}",
                task="variable_extraction",
            )
            ## EVAL VARIABLE EXTRACTION
            if result["result"]["job_result"]:
                # Evaluate accuracy
                ground_truth_path = f"scenarios/{scenario}/ground_truth/variable_extraction.json"
                if os.path.exists(ground_truth_path):
                    logging.info(f"Accuracy for {scenario}:{task}")
                    generated_extractions = json.dumps(result["result"]["job_result"]["extraction"])
                    with open(ground_truth_path) as file:
                        truth = file.read()
                        files = {
                            "extractions_file": ("paper_variable_extractions.json", generated_extractions),
                            "gt_annotations": ("paper_gt_annotations.json", truth),
                            "json_text": ("paper_cosmos_output.json", json.dumps(cosmos_extraction_json))
                        }
                        eval = requests.post(
                            f"{TA1_UNIFIED_URL}/text-reading/eval",
                            files=files,
                        )
                        if eval.status_code < 300:
                            result["accuracy"] = eval.json()
                        else:
                            result["accuracy"] = {"status_code": eval.status_code}
                else:
                    logging.info(f"No ground truth exists for: {scenario}:{task}")
                    result["accuracy"] = None
            else:
                result["accuracy"] = None

            yield task, result

    # STEP 3: CODE TO AMR
    # Try dynamics only since code_to_amr fallsback to full repo if dynamics fails
    code_exists = True
    code_response = auth_session().get(f"{TDS_URL}/code-asset/{code_id}")
    if code_response.status_code > 300:
        code_exists = False
        yield non_applicable_run("code_to_amr")
    else:
        (task, result) = do_task(
            url=f"{KM_URL}/code_to_amr?code_id={code_id}&model_id={model_id}&dynamics_only=True&name={scenario}",
            task="code_to_amr",
        )
        if result["success"]:
            model_exists = True
            add_asset(model_id, "model", project_id)
            add_provenance(left_id=model_id,
                           left_type="Model",
                           right_id=code_id,
                           right_type="Code",
                           relation_type="EXTRACTED_FROM")
        else:
            logging.error(
                f"Model was not generated from code for scenario: {scenario}, amr creation response: {result}"
            )
        yield task, result

    # Step 3.5: EQUATIONS TO AMR
    latex_path = f"scenarios/{scenario}/equations.latex.txt"
    mathml_path = f"scenarios/{scenario}/equations.mathml.txt"
    file_path = None
    equation_type = None
    equations_exists = True
    if os.path.exists(latex_path):
        file_path = latex_path
        equation_type = "latex"
    elif os.path.exists(mathml_path):
        file_path = mathml_path
        equation_type = "mathml"
    else:
        equations_exists = False
        yield non_applicable_run("equations_to_amr")

    if file_path and equation_type:
        with open(file_path) as file:
            equations = file.read()
            parameters_payload = {
                "equation_type": equation_type,
            }
            (task, result) = do_task(
                url=f"{KM_URL}/equations_to_amr?name={scenario}&model_id={model_id}",
                task="equations_to_amr",
                kwargs={"params": parameters_payload, "data": equations},
            )

            if result["success"]:
                model_exists = True
                add_asset(model_id, "model", project_id)
            else:
                logging.error(
                    f"Model was not generated from equations for scenario: {scenario}, amr creation response: {result}"
                )
            yield task, result

    # STEP 4: PROFILE AMR
    if not code_exists and not equations_exists:
        yield non_applicable_run("profile_model")
    elif not model_exists and (code_exists or equations_exists):
        yield upstream_failure("profile_model")
    else:
        # Check if document exists in TDS and change URL based on that.
        document_response = auth_session().get(f"{TDS_URL}/document-asset/{scenario}")
        if document_response.status_code > 300:
            model_suffix = f"{model_id}"
        else:
            model_suffix = f"{model_id}?document_id={document_id}"

        (task, result) = do_task(
            url=f"{KM_URL}/profile_model/{model_suffix}",
            task="profile_model",
        )

        # Scrub OpenAI key from error logs as needed
        try:
            if "job_error" in result.get("result", {}):
                result["result"]["job_error"] = result["result"]["job_error"].replace(
                    OPENAI_API_KEY, "OPENAI KEY REDACTED"
                )
        except Exception as e:
            logging.error(e)

        ## EVAL STEP 4
        if result["result"]["job_result"]:
            # Evaluate accuracy
            ground_truth_path = f"scenarios/{scenario}/ground_truth/model_card.json"
            if os.path.exists(ground_truth_path):
                logging.info(f"Accuracy for {scenario}:{task}")
                generated_card = json.dumps(result["result"]["job_result"]["card"])
                with open(ground_truth_path) as file:
                    truth = file.read()
                    files = {
                        "test_json_file": generated_card,
                        "ground_truth_file": truth,
                    }
                    eval = requests.post(
                        f"{MIT_TR_URL}/evaluation/eval_model_card",
                        params={"gpt_key": OPENAI_API_KEY},
                        files=files,
                    )
                    if eval.status_code < 300:
                        result["accuracy"] = eval.json()
                    else:
                        result["accuracy"] = {"status_code": eval.status_code}
            else:
                logging.info(f"No ground truth exists for: {scenario}:{task}")
                result["accuracy"] = None
        else:
            result["accuracy"] = None

        yield task, result

    # STEP 5: LINK AMR
    # Check if document exists
    document_response = auth_session().get(f"{TDS_URL}/document-asset/{document_id}")
    if document_response.status_code > 300:
        yield non_applicable_run("link_amr")
    elif not document_response.json().get('metadata'):
        # no variables were extracted
        yield upstream_failure("link_amr")
    # Check if code ore equations exist
    elif not code_exists and not equations_exists:
        yield non_applicable_run("link_amr")
    elif not model_exists and (code_exists or equations_exists):
        yield upstream_failure("link_amr")
    else:
        document_response = auth_session().get(f"{TDS_URL}/document-asset/{document_id}")
        if document_response.status_code > 300:
            yield non_applicable_run("link_amr")
        else:
            document = document_response.json()
            if document["metadata"] is None:
                yield upstream_failure("link_amr")
            else:
                add_provenance(left_id=model_id,
                               left_type="Model",
                               right_id=document_id,
                               right_type="Document",
                               relation_type="EXTRACTED_FROM")
                (task, result) = do_task(
                    url=f"{KM_URL}/link_amr?document_id={document_id}&model_id={model_id}",
                    task="link_amr",
                )
                ## EVAL AMR LINKING
                if result["result"]["job_result"]:
                    # Evaluate accuracy
                    ground_truth_path = f"scenarios/{scenario}/ground_truth/linked_amr.json"
                    if os.path.exists(ground_truth_path):
                        logging.info(f"Accuracy for {scenario}:{task}")
                        generated_amr = json.dumps(result["result"]["job_result"]["amr"])
                        with open(ground_truth_path) as file:
                            truth = file.read()
                            files = {
                                "linked_amr": ("linked_amr_file.json", generated_amr),
                                "gt_annotations": ("gt_linked_amr_file.json", truth),
                            }
                            eval = requests.post(
                                f"{TA1_UNIFIED_URL}/metal/eval",
                                files=files,
                            )
                            if eval.status_code < 300:
                                result["accuracy"] = eval.json()
                            else:
                                result["accuracy"] = {"status_code": eval.status_code}
                    else:
                        logging.info(f"No ground truth exists for: {scenario}:{task}")
                        result["accuracy"] = None
                else:
                    result["accuracy"] = None
                yield task, result

    # STEP 6: PROFILE DATASET
    if os.path.exists(f"scenarios/{scenario}/dataset.csv"):
        if document_id:
            dataset_url = f"{KM_URL}/profile_dataset/{dataset_id}?document_id={document_id}"
            add_provenance(left_id=dataset_id,
                            left_type="Dataset",
                            right_id=document_id,
                            right_type="Document",
                            relation_type="EXTRACTED_FROM")
        else:
            dataset_url = f"{KM_URL}/profile_dataset/{dataset_id}"
        (task, result) = do_task(
            url=dataset_url,
            task="profile_dataset",
        )

        # Scrub OpenAI key from error logs as needed
        try:
            if "job_error" in result.get("result", {}):
                result["result"]["job_error"] = result["result"]["job_error"].replace(
                    OPENAI_API_KEY, "OPENAI KEY REDACTED"
                )
        except Exception as e:
            logging.error(e)

        yield task, result

    else:
        yield non_applicable_run("profile_dataset")


def pipeline(scenario, _id):
    shape = [
        {"from": "pdf_extraction", "to": "variable_extraction", "link_type": "hard"},
        {"from": "pdf_extraction", "to": "profile_dataset", "link_type": "soft"},
        {"from": "pdf_extraction", "to": "profile_model", "link_type": "soft"},
        {"from": "variable_extraction", "to": "link_amr", "link_type": "hard"},
        {"from": "code_to_amr", "to": "profile_model", "link_type": "hard"},
        {"from": "code_to_amr", "to": "link_amr", "link_type": "hard"},
        {"from": "equations_to_amr", "to": "link_amr", "link_type": "hard"},
        {"from": "equations_to_amr", "to": "profile_model", "link_type": "hard"},
        {"from": "profile_model", "to": "link_amr", "link_type": "soft"},
    ]
    report = {}
    # remaining_steps = {edge["to"] for edge in shape}.union(
    #     {edge["from"] for edge in shape}
    # )
    success = True
    for task, result in standard_flow(scenario, _id):
        report[task] = result
        if result["success"] is False:
            success = False
        # remaining_steps.remove(task)
        # if not result["success"]:
        #     logging.error(
        #         f"Pipeline did not complete on scenario: {scenario}, error: {result['result']['job_error']}"
        #     )
        #     break

    # for task in remaining_steps:
    #     report[task] = {"success": None, "time": 0, "accuracy": None}

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
        "project_id": project_id
    }
    return {scenario: pipeline_report}


if __name__ == "__main__":
    # Try to get the first argument from CLI as a list
    if not os.path.exists('project_id.txt'):
        raise Exception("No project ID found")
    else:
        project_id = open('project_id.txt','r').read()

    if len(sys.argv) > 1:
        filepath = "./scenarios/"
        scenarios = sys.argv[1:]
        logging.info(f"Running pipeline on scenarios: {scenarios}")
    else:
        scenarios = os.listdir("./scenarios")
        logging.info(f"Running pipeline on all scenarios")

    reports = []
    for scenario in scenarios:
        _id = f"{project_id}-{scenario.replace(' ','-')}"

        logging.info(f"Pipeline running on: {scenario} with _id {_id}")
        report = pipeline(scenario, _id)

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
