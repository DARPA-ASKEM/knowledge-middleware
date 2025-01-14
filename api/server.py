# LOGGING
import logging
import os
from enum import Enum
from typing import Annotated, List, Optional

from fastapi import FastAPI, HTTPException, Path, Depends, status
from fastapi.middleware.cors import CORSMiddleware

from api.models import EquationType, ExtractionJob, DomainType
from api.utils import create_job, fetch_job_status, get_redis
from lib.settings import settings

LOG_LEVEL = settings.LOG_LEVEL
numeric_level = getattr(logging, LOG_LEVEL, None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {LOG_LEVEL}")
logging.basicConfig()
logging.getLogger().setLevel(numeric_level)


def build_api(*args) -> FastAPI:
    api = FastAPI(
        title="Terarium Knowledge Middleware Service",
        description="Middleware for managing interactions with various services.",
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
def get_status(extraction_job_id: str, redis=Depends(get_redis)) -> ExtractionJob:
    """
    Retrieve the status of a extraction
    """

    extraction_job_status = fetch_job_status(extraction_job_id, redis)
    if (
        isinstance(extraction_job_status, int)
        and extraction_job_status == status.HTTP_404_NOT_FOUND
    ):
        raise HTTPException(
            status_code=404,
            detail=f"Extraction Job with ID {extraction_job_id} not found",
        )
    return extraction_job_status


@app.post("/equations_to_amr")
def equations_to_amr(
    payload: List[str],
    equation_type: EquationType,
    model: str = "petrinet",
    model_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    redis=Depends(get_redis),
) -> ExtractionJob:
    """Post equations and store an AMR to TDS

    Args:
    ```
        payload (List[str]): A list of LaTeX or MathML strings representing the functions that are used to convert to AMR
        equation_type (str): [latex, mathml]
        model (str, optional): AMR model return type. Defaults to "petrinet". Options: "regnet", "petrinet".
        model_id (str, optional): the id of the model (to update/create) based on the set of equations
        name (str, optional): the name to set on the newly created model
        description (str, optional): the description to set on the newly created model
    ```
    """

    operation_name = "operations.equations_to_amr"
    options = {
        "equations": payload,
        "equation_type": equation_type.value,
        "model": model,
        "model_id": model_id,
        "name": name,
        "description": description,
    }

    resp = create_job(operation_name=operation_name, options=options, redis=redis)

    return resp


@app.post("/code_to_amr")
def code_to_amr(
    code_id: str,
    name: Optional[str] = None,
    model_id: Optional[str] = None,
    description: Optional[str] = None,
    llm_assisted: Optional[bool] = True,    
    dynamics_only: Optional[bool] = False,
    redis=Depends(get_redis),
) -> ExtractionJob:
    """
    Converts a code object to an AMR. Assumes that the code file is the first
    file (and only) attached to the code.

    Args:
    ```
        code_id (str): the id of the code
        name (str, optional): the name to set on the newly created model
        model_id (str, optional): the id of the model (to create) based on the code
        description (str, optional): the description to set on the newly created model
        llm_assisted: (bool, optional): whether to use SKEMA's LLM assisted dynamics extraction prior to submission of a zipfile; cannot be used in conjunction with `dynamics_only`        
        dynamics_only (bool, optional): whether to only run the amr extraction over specified dynamics from the code object in TDS; cannot be used in conjunction with `llm_assisted`
    ```
    """
    operation_name = "operations.code_to_amr"
    options = {
        "code_id": code_id,
        "name": name,
        "model_id": model_id,
        "description": description,
        "dynamics_only": dynamics_only,
        "llm_assisted": llm_assisted,
    }

    resp = create_job(operation_name=operation_name, options=options, redis=redis)

    return resp


@app.post("/pdf_extraction")
def pdf_extraction(
    document_id: str, force_run: bool = False, redis=Depends(get_redis)
) -> ExtractionJob:
    """Run Cosmos extractions over pdfs and stores the text/assets on the document

    Args:
        `document_id`: the id of the document to process
        `force_run`: boolean whether to force a Cosmos run; if False and the PDF is in Cosmos's cache,
                     the cache will be used. If True, the cache will ignored and Cosmos will be force run.
    """
    operation_name = "operations.pdf_extraction"

    options = {"document_id": document_id, "force_run": force_run}

    resp = create_job(operation_name=operation_name, options=options, redis=redis)

    return resp


@app.post("/variable_extractions")
async def variable_extractions(
    document_id: str,
    annotate_skema: bool = True,
    annotate_mit: bool = True,
    name: str = None,
    description: str = None,
    domain: DomainType = DomainType.EPI,
    redis=Depends(get_redis),
) -> ExtractionJob:
    """Run variable extractions over document

    Args:
    ```
        * document_id: [str] the ID of the document in TDS to extract from; must have `text` extracted already via `/pdf_extraction`
        * annotate_skema: [bool] should SKEMA system be used
        * annotate_mit: [bool] should MIT system be used
        * name: [str] name to give to the document (optional)
        * description: [str] description to apply to document (optional)
        * domain: [epi, climate] the knowledge graph domain to use (only used by MIT system)
    ```
    """
    operation_name = "operations.variable_extractions"

    # text_content = text_content[: len(text_content) // 2]
    options = {
        "document_id": document_id,
        "annotate_skema": annotate_skema,
        "annotate_mit": annotate_mit,
        "name": name,
        "description": description,
        "domain": domain.value,
    }

    resp = create_job(operation_name=operation_name, options=options, redis=redis)

    return resp


@app.post("/profile_dataset/{dataset_id}")
def profile_dataset(
    dataset_id: str,
    document_id: Optional[str] = None,
    redis=Depends(get_redis),
) -> ExtractionJob:
    """Profile dataset with MIT's profiling service. This optionally accepts an `document_id` which
    is expected to be some user uploaded document which has had its text extracted and stored as
    the `text` element on the document.

    > NOTE: if nothing is found within `text` of the document then it is ignored.

    Args:
        dataset_id: the id of the dataset to profile
        document_id [optional]: the id of the document (paper/resource) associated with the dataset.
    """
    operation_name = "operations.data_card"

    options = {
        "dataset_id": dataset_id,
        "document_id": document_id,
    }

    resp = create_job(operation_name=operation_name, options=options, redis=redis)

    return resp


@app.post("/profile_model/{model_id}")
def profile_model(
    model_id: str,
    document_id: Optional[str] = None,
    redis=Depends(get_redis),
) -> ExtractionJob:
    """Profile model with MIT's profiling service. This takes in a paper and code document
    and updates a model (AMR) with the profiled metadata card. It requires that the paper
    has been extracted with `/pdf_extraction` and the code has been converted to an AMR
    with `/code_to_amr`

    > NOTE: if nothing the paper is not extracted and the model not created from code this WILL fail.

    Args:
        model_id: the id of the model to profile
        paper_document_id: the id of the paper document
    """
    operation_name = "operations.model_card"

    options = {"model_id": model_id, "paper_document_id": document_id}

    resp = create_job(operation_name=operation_name, options=options, redis=redis)

    return resp


@app.post("/link_amr")
def link_amr(
    document_id: str,
    model_id: str,
    redis=Depends(get_redis),
) -> ExtractionJob:
    operation_name = "operations.link_amr"

    options = {
        "document_id": document_id,
        "model_id": model_id,
    }

    resp = create_job(operation_name=operation_name, options=options, redis=redis)

    return resp
