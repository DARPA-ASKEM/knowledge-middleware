from glob import glob
import logging
import json
import os

import requests
import zipfile
import tempfile

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

TDS_URL = os.environ.get("TDS_URL", "http://data-service:8000")


def add_code(scenario):
    file_paths = [
        f"./scenarios/{scenario}/code.py",
        f"./scenarios/{scenario}/code.zip",
        f"./scenarios/{scenario}/dynamics.*",
    ]
    existing_filepath = None

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
                "id": scenario,
                "name": scenario,
                "description": "",
                "files": {
                    f"{existing_filepath.split('/')[-1]}": dynamics,
                },
                "repo_url": "",
            }

            code_response = requests.post(
                TDS_URL + "/code",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if code_response.status_code >= 300:
                raise Exception(
                    f"Failed to POST code ({code_response.status_code}): {scenario}"
                )

            url_response = requests.get(
                TDS_URL + f"/code/{scenario}/upload-url",
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

    elif existing_filepath.endswith(".py"):
        logging.info(f"Adding {scenario} code")
        payload = {
            "id": scenario,
            "name": scenario,
            "description": "",
            "files": {
                "code.py": {
                    "language": "python",
                },
            },
            "repo_url": "https://github.com/owner/repo.git",
            "commit": "seed",
            "branch": "seed",
        }

        code_response = requests.post(
            TDS_URL + "/code",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        if code_response.status_code >= 300:
            raise Exception(
                f"Failed to POST code ({code_response.status_code}): {scenario}"
            )

        url_response = requests.get(
            TDS_URL + f"/code/{scenario}/upload-url", params={"filename": "code.py"}
        )
        upload_url = url_response.json()["url"]
        with open(filepath, "rb") as file:
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
            files_object = {}
            for extracted_file in extracted_files:
                extracted_filepath = os.path.join(temp_dir, extracted_file)
                # Process each extracted file as needed
                files_object[extracted_file] = {}

            payload = {
                "id": scenario,
                "name": scenario,
                "description": "",
                "files": files_object,
                "repo_url": "https://github.com/owner/repo.git",
                "commit": "seed",
                "branch": "seed",
            }

            logging.info(f"Payload: s{payload}")

            code_response = requests.post(
                TDS_URL + "/code",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if code_response.status_code >= 300:
                raise Exception(
                    f"Failed to POST code ({code_response.status_code}): {scenario}"
                )

            for extracted_file in extracted_files:
                filepath = os.path.join(temp_dir, extracted_file)
                url_response = requests.get(
                    TDS_URL + f"/code/{scenario}/upload-url",
                    params={"filename": extracted_file},
                )
                upload_url = url_response.json()["url"]
                with open(filepath, "rb") as file:
                    upload_response = requests.put(upload_url, file)

                    if upload_response.status_code >= 300:
                        raise Exception(
                            f"Failed to upload code ({upload_response.status_code}): {scenario}"
                        )
                    else:
                        logging.info(f"Uploaded {scenario} code")
    else:
        return


def add_paper(scenario):
    filepath = f"./scenarios/{scenario}/paper.pdf"
    if not os.path.exists(filepath):
        return
    logging.info(f"Adding {scenario} paper")
    payload = {
        "id": scenario,
        "name": scenario,
        "username": "Adam Smith",
        "description": "",
        "timestamp": "2023-08-30T14:53:12.994Z",
        "file_names": ["paper.pdf"],
        "metadata": {},
        "document_url": "https://github.com/owner/repo/blob/main/paper.pdf",
        "source": "Science Advances",
        "text": "",
        "grounding": {"identifiers": {}, "context": {}},
        "assets": [],
    }

    paper_response = requests.post(
        TDS_URL + "/documents",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    if paper_response.status_code >= 300:
        raise Exception(
            f"Failed to POST code ({paper_response.status_code}): {scenario}"
        )

    url_response = requests.get(
        TDS_URL + f"/documents/{scenario}/upload-url", params={"filename": "paper.pdf"}
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


def add_dataset(scenario):
    filepath = f"./scenarios/{scenario}/dataset.csv"
    if not os.path.exists(filepath):
        return
    logging.info(f"Adding {scenario} dataset")
    payload = {
        "id": scenario,
        "name": scenario,
        "username": "Adam Smith",
        "description": "",
        "file_names": ["dataset.csv"],
        "metadata": {},
    }

    dataset_response = requests.post(
        TDS_URL + "/datasets",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    if dataset_response.status_code >= 300:
        raise Exception(
            f"Failed to POST dataset ({dataset_response.status_code}): {scenario}"
        )

    url_response = requests.get(
        TDS_URL + f"/datasets/{scenario}/upload-url", params={"filename": "dataset.csv"}
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


for scenario in os.listdir("./scenarios"):
    logging.info(f"Seeding {scenario}")
    add_code(scenario)
    add_paper(scenario)
    add_dataset(scenario)
