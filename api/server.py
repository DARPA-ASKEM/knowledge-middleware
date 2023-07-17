from __future__ import annotations

import io

import pypdf

from typing import List

from fastapi import FastAPI, Response, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware


def build_api(*args) -> FastAPI:
    api = FastAPI(
        title="TA 1 Extraction Service",
        description="Service for running the extraction pipelines from artifact to AMR.",
        docs_url="/",
    )
    origins = [
        "http://localhost",
        "http://localhost:8080",
    ]
    api.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return api


app = build_api()


@app.get("/status/{extraction_job_id}")
def get_status(extraction_job_id: str):
    """
    Retrieve the status of a extraction
    """
    from utils import fetch_job_status

    status, result = fetch_job_status(extraction_job_id)
    if not isinstance(status, str):
        return status

    return {"status": status, "result": result}


@app.post("/mathml_to_amr")
def mathml_to_amr(payload: List[str], model: str = "petrinet"):
    """Post MathML to skema service to get AMR return

    Args:
        payload (List[str]): A list of MathML strings representing the functions that are used to convert to AMR
        model (str, optional): AMR model return type. Defaults to "petrinet". Options: "regnet", "petrinet".
    """
    from utils import create_job

    operation_name = "operations.put_mathml_to_skema"
    options = {"mathml": payload, "model": model}

    resp = create_job(operation_name=operation_name, options=options)

    return resp


@app.post("/code_to_amr")
def code_to_amr(artifact_id: str):
    from utils import create_job

    operation_name = "operations.code_to_amr"
    options = {"artifact_id": artifact_id}

    resp = create_job(operation_name=operation_name, options=options)

    return resp


@app.post("/pdf_extractions")
async def pdf_extractions(
    artifact_id: str,
    annotate_skema: bool = True,
    annotate_mit: bool = True,
    name: str = None,
    description: str = None,
):
    """Run text extractions over pdfs

    Args:
        pdf (UploadFile, optional): The pdf to run extractions over. Defaults to File(...).
    """

    from utils import create_job

    operation_name = "operations.pdf_extractions"

    # text_content = text_content[: len(text_content) // 2]
    options = {
        "artifact_id": artifact_id,
        "annotate_skema": annotate_skema,
        "annotate_mit": annotate_mit,
        "name": name,
        "description": description,
    }

    resp = create_job(operation_name=operation_name, options=options)

    return resp


@app.post("/profile_dataset/{dataset_id}")
def profile_dataset_document(dataset_id: str):
    from utils import create_job

    operation_name = "operations.dataset_profiling"

    options = {
        "dataset_id": dataset_id,
    }

    resp = create_job(operation_name=operation_name, options=options)

    return resp


@app.post("/profile_dataset/{dataset_id}/{artifact_id}")
def profile_dataset_document(dataset_id: str, artifact_id: str = None):
    from utils import create_job

    operation_name = "operations.dataset_profiling_with_document"

    options = {
        "dataset_id": dataset_id,
        "artifact_id": artifact_id,
    }

    resp = create_job(operation_name=operation_name, options=options)

    return resp


@app.post("/link_amr")
def link_amr(artifact_id: str, model_id: str):
    from utils import create_job

    operation_name = "operations.link_amr"

    options = {
        "artifact_id": artifact_id,
        "model_id": model_id,
    }

    resp = create_job(operation_name=operation_name, options=options)

    return resp
