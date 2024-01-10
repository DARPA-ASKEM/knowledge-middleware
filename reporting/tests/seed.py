from glob import glob
import logging
import json
import os
import time
from datetime import datetime
from api.tds import tds_session
import sys

import requests
import zipfile
import tempfile

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

TDS_URL = os.environ.get("TDS_URL", "http://data-service:8000")

def create_project():
    '''
    Generate test project in TDS
    '''
    current_timestamp = datetime.now()
    ts = current_timestamp.strftime('%Y-%m-%d %H:%M:%S')

    project = {
        "name": "Integration Test Suite Project",
        "description": f"Test generated at {ts}",
        "projectAssets": [],
        }

    resp = tds_session().post(f"{TDS_URL}/projects", json=project)
    project_id = resp.json()['id']

    return project_id

def add_asset(resource_id, resource_type, project_id):
    resp = tds_session().post(f"{TDS_URL}/projects/{project_id}/assets/{resource_type}/{resource_id}")
    return resp.json()

def add_code(scenario, project_id, file_path_override=None):
    file_paths = [
        f"./scenarios/{scenario}/code.zip",
        f"./scenarios/{scenario}/dynamics.*",
        f"./scenarios/{scenario}/repo_url.txt",
    ]
    existing_filepath = None

    if file_path_override:
        existing_filepath = file_path_override
    else:
        for filepath in file_paths:
            if os.path.exists(filepath):
                existing_filepath = filepath
                break  # Found a file, so stop looking
            # Wildcard support for dynamics files.
            matching_paths = glob(filepath)
            logging.info(f"Matching paths: {matching_paths}")
            if matching_paths:
                existing_filepath = matching_paths[0]
                break

    if existing_filepath is None:
        return

    if existing_filepath.split("/")[-1].startswith("dynamics."):
        logging.info(f"Adding {scenario} dynamics code")

        with open(existing_filepath) as file:
            line_count = sum(1 for line in file)
            dynamics_code = file.read()

            block_start = "L1"
            block_end = f"L{line_count}"
            dynamics = {
                "block": [f"{block_start}-{block_end}"],
            }
            payload = {
                "name": scenario,
                "description": "",
                "files": {
                    f"{existing_filepath.split('/')[-1]}": dynamics,
                },
                "repo_url": "",
            }

            code_response = tds_session().post(
                TDS_URL + "/code-asset",
                json=payload,
            )

            if code_response.status_code >= 300:
                raise Exception(
                    f"Failed to POST code ({code_response.status_code}): {scenario}"
                )
            else:
                add_asset(code_response.json()['id'], "code", project_id)

            url_response = tds_session().get(
                TDS_URL + f"/code-asset/{code_response.json()['id']}/upload-url",
                params={"filename": existing_filepath.split("/")[-1]},
            )
            upload_url = url_response.json()["url"]
            with open(existing_filepath) as file:
                upload_response = requests.put(upload_url, file)

                if upload_response.status_code >= 300:
                    raise Exception(
                        f"Failed to upload code ({upload_response.status_code}): {scenario}"
                    )
                else:
                    logging.info(f"Uploaded {scenario} code")


    elif existing_filepath.endswith(".zip"):
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(existing_filepath, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Loop through the extracted files
            extracted_files = [
                file for file in zip_ref.namelist() if not file.endswith("/")
            ]
            logging.info(f"Extracted files: {extracted_files}")
            files_object = {}
            for extracted_file in extracted_files:
                extracted_filepath = os.path.join(temp_dir, extracted_file)
                # Process each extracted file as needed
                files_object[extracted_file] = {}

            payload = {
                "name": scenario,
                "description": "",
                "files": files_object,
                "repo_url": "https://github.com/owner/repo.git",
                "commit": "seed",
                "branch": "seed",
            }

            logging.info(f"Payload: {payload}")

            code_response = tds_session().post(
                TDS_URL + "/code-asset",
                json=payload,
            )
            if code_response.status_code >= 300:
                raise Exception(
                    f"Failed to POST code ({code_response.status_code}): {scenario}"
                )
            else:
                add_asset(code_response.json()['id'], "code", project_id)

            for extracted_file in extracted_files:
                filepath = os.path.join(temp_dir, extracted_file)
                url_response = requests.get(
                    TDS_URL + f"/code-asset/{code_response.json()['id']}/upload-url",
                    params={"filename": extracted_file},
                )
                upload_url = url_response.json()["url"]
                file_size = os.path.getsize(filepath)
                logging.info(f"{extracted_file} size: {file_size}")
                if file_size == 0:
                    continue

                with open(filepath, "rb") as file:
                    headers = {"Content-Length": str(file_size)}
                    upload_response = requests.put(upload_url, file, headers=headers)

                    if upload_response.status_code >= 300:
                        raise Exception(
                            f"Failed to upload code ({upload_response.status_code}): {scenario}"
                        )
                    else:
                        logging.info(f"Uploaded {scenario} code")

    elif existing_filepath.endswith(".txt"):
        logging.info(f"Adding {scenario} repo_url")
        with open(existing_filepath) as file:
            # This should already be a link to the archive zipfile on GitHub
            # Example: https://github.com/username/repository/archive/main.zip
            repo_archive_url = file.read()

            response = requests.get(repo_archive_url)

            if response.status_code == 200:
                with open(f"./scenarios/{scenario}/code.zip", "wb") as file:
                    file.write(response.content)

            add_code(scenario, project_id, file_path_override=f"./scenarios/{scenario}/code.zip")
    else:
        return


def add_paper(scenario, project_id):
    filepath = f"./scenarios/{scenario}/paper.pdf"
    if not os.path.exists(filepath):
        return
    logging.info(f"Adding {scenario} paper")


    payload = {
        "name": scenario,
        "username": "Adam Smith",
        "description": "",
        "timestamp": "2023-08-30T14:53:12.994Z",
        "file_names": ["paper.pdf"],
        "metadata": {},
        "document_url": "https://github.com/owner/repo/blob/main/paper.pdf",
        "source": "Science Advances",
        "text": None,
        "grounding": {"identifiers": {}, "context": {}},
        "assets": [],
    }

    paper_response = tds_session().post(
        TDS_URL + "/documents",
        json=payload,
    )
    if paper_response.status_code >= 300:
        raise Exception(
            f"Failed to POST code ({paper_response.status_code}): {scenario}"
        )
    else:
        add_asset(paper_response.json()['id'], "document", project_id)

    url_response = tds_session().get(
        TDS_URL + f"/documents/{paper_response.json()['id']}/upload-url", params={"filename": "paper.pdf"}
    )
    upload_url = url_response.json()["url"]
    with open(filepath, "rb") as file:
        upload_response = requests.put(upload_url, file)

        if upload_response.status_code >= 300:
            raise Exception(
                f"Failed to upload code ({upload_response.status_code}): {scenario}"
            )
        else:
            logging.info(f"Uploaded {scenario} paper")


def add_dataset(scenario, project_id):
    filepath = f"./scenarios/{scenario}/dataset.csv"
    if not os.path.exists(filepath):
        return
    logging.info(f"Adding {scenario} dataset")

    payload = {
        "name": scenario,
        "username": "Adam Smith",
        "description": "",
        "file_names": ["dataset.csv"],
        "metadata": {},
    }

    dataset_response = tds_session().post(
        TDS_URL + "/datasets",
        json=payload,
    )

    if dataset_response.status_code >= 300:
        raise Exception(
            f"Failed to POST dataset ({dataset_response.status_code}): {scenario}"
        )
    else:
        add_asset(dataset_response.json()['id'], "dataset", project_id)

    url_response = tds_session().get(
        TDS_URL + f"/datasets/{dataset_response.json()['id']}/upload-url", params={"filename": "dataset.csv"}
    )

    upload_url = url_response.json()["url"]
    with open(filepath, "rb") as file:
        upload_response = requests.put(upload_url, file)

        if upload_response.status_code >= 300:
            raise Exception(
                f"Failed to upload dataset ({upload_response.status_code}): {scenario}"
            )
        else:
            logging.info(f"Uploaded {scenario} dataset")

if __name__ == "__main__":
    # Try to get the first argument from CLI as a list

    if len(sys.argv) > 1:
        filepath = "./scenarios/"
        scenarios = sys.argv[1:]
        logging.info(f"Running pipeline on scenarios: {scenarios}")
    else:
        scenarios = os.listdir("./scenarios")
        logging.info(f"Running pipeline on all scenarios")

    # Get project ID from environment
    project_id = os.environ.get("PROJECT_ID")
    if project_id:
        logging.info(f"Project ID found in environment: {project_id}")
        proj_resp = tds_session().get(f"{TDS_URL}/projects/{project_id}")
        if proj_resp.status_code == 404:
            raise Exception(f"Project ID {project_id} does not exist in TDS at {TDS_URL}")
    # if it does not exist, create it
    else:
        project_id = create_project()
        logging.info(f"No project ID found in environment. Created project with ID: {project_id}")

    for scenario in scenarios:
        logging.info(f"Seeding {scenario} to project {project_id}")
        add_code(scenario, project_id)
        add_paper(scenario, project_id)
        add_dataset(scenario, project_id)

        with open('project_id.txt', 'w') as f:
            f.write(f"{project_id}")
