from __future__ import annotations

import io

import pypdf

from typing import List, Optional
from enum import Enum

from fastapi import FastAPI, Response, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

class EquationType(Enum):
    LATEX = "latex"
    MATHML = "mathml"

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


@app.post("/equations_to_amr")
def equations_to_amr(payload: List[str], 
                     equation_type: EquationType, 
                     model: str = "petrinet", 
                     name: Optional[str] = None, 
                     description: Optional[str] = None):
    """Post equations and store an AMR to TDS

    Args:
    ```
        payload (List[str]): A list of Latex or MathML strings representing the functions that are used to convert to AMR
        equation_type (str): [latex, mathml]
        model (str, optional): AMR model return type. Defaults to "petrinet". Options: "regnet", "petrinet".
        name (str, optional): the name to set on the newly created model
        description (str, optional): the description to set on the newly created model        
    ```
    """
    from utils import create_job
    
    operation_name = "operations.equations_to_amr"
    options = {"equations": payload, 
               "equation_type": equation_type.value, 
               "model": model,
               "name": name,
               "description": description}

    resp = create_job(operation_name=operation_name, options=options)

    return resp

@app.post("/code_to_amr")
def code_to_amr(artifact_id: str, 
                name: Optional[str] = None, 
                description: Optional[str] = None):
    """
    Converts a code artifact to an AMR. Assumes that the code file is the first
    file (and only) attached to the artifact.

    Args:
    ```
        artifact_id (str): the id of the code artifact
        name (str, optional): the name to set on the newly created model
        description (str, optional): the description to set on the newly created model
    ```
    """
    from utils import create_job

    operation_name = "operations.code_to_amr"
    options = {"artifact_id": artifact_id,
               "name": name,
               "description": description}

    resp = create_job(operation_name=operation_name, options=options)

    return resp

@app.post("/pdf_to_text")
async def pdf_to_text(
    artifact_id: str
):
    """Run text extractions over pdfs and stores the text as metadata on the artifact

    Args:
        `artifact_id`: the id of the artifact to process
    """

    from utils import create_job

    operation_name = "operations.pdf_to_text"

    options = {
        "artifact_id": artifact_id
    }

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
def profile_dataset(dataset_id: str, artifact_id: Optional[str] = None):
    """Profile dataset with MIT's profiling service. This optionally accepts an `artifact_id` which 
    is expected to be some user uploaded document which has had its text extracted and stored to 
    `metadata.text`.

    > NOTE: if nothing is found within `metadata.text` of the artifact then it is ignored.

    Args:
        dataset_id: the id of the dataset to profile
        artifact_id [optional]: the id of the artifact (paper/document) associated with the dataset.
    """    
    from utils import create_job

    operation_name = "operations.dataset_card"

    options = {
        "dataset_id": dataset_id,
        "artifact_id": artifact_id,
    }

    resp = create_job(operation_name=operation_name, options=options)

    return resp

@app.post("/profile_model/{model_id}")
def profile_model(model_id: str, paper_artifact_id: str):
    """Profile model with MIT's profiling service. This takes in a paper and code artifact 
    and updates a model (AMR) with the profiled metadata card. It requires that the paper
    has been extracted with `/pdf_to_text` and the code has been converted to an AMR
    with `/code_to_amr`

    > NOTE: if nothing the paper is not extracted and the model not created from code this WILL fail.

    Args:
        model_id: the id of the model to profile
        paper_artifact_id: the id of the paper artifact
    """    
    from utils import create_job

    operation_name = "operations.model_card"

    options = {
        "model_id": model_id,
        "paper_artifact_id": paper_artifact_id
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
