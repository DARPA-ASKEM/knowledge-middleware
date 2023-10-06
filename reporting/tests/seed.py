from glob import glob
import logging
import json
import os

import requests

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

TDS_URL = os.environ.get("TDS_URL", "http://data-service:8000")

def add_code(scenario):
  filepath = f"./scenarios/{scenario}/code.py"  
  if not os.path.exists(filepath):
    return
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
    "branch": "seed"
  }
  
  code_response = requests.post(TDS_URL + "/code", json=payload, headers={
    "Content-Type": "application/json"
  })
  if code_response.status_code >= 300:
    raise Exception(f"Failed to POST code ({code_resonse.status_code}): {scenario}")

  url_response = requests.get(TDS_URL + f"/code/{scenario}/upload-url", params={"filename": "code.py"})
  upload_url = url_response.json()["url"]
  with open(filepath, "rb") as file:
      requests.put(upload_url, file)


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
    "file_names": [
      "paper.pdf"
    ],
    "metadata": {},
    "document_url": "https://github.com/owner/repo/blob/main/paper.pdf",
    "source": "Science Advances",
    "text": "",
    "grounding": {
      "identifiers": {},
      "context": {}
    },
    "assets": []
  }
  
  paper_response = requests.post(TDS_URL + "/documents", json=payload, headers={
    "Content-Type": "application/json"
  })
  if paper_response.status_code >= 300:
    raise Exception(f"Failed to POST code ({paper_resonse.status_code}): {scenario}")

  url_response = requests.get(TDS_URL + f"/code/{scenario}/upload-url", params={"filename": "paper.pdf"})
  upload_url = url_response.json()["url"]
  with open(filepath, "rb") as file:
      requests.put(upload_url, file)


for scenario in os.listdir("./scenarios"):
  logging.info(f"Seeding {scenario}")  
  add_code(scenario)
  add_paper(scenario)
