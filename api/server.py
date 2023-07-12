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


@app.get("/status/{simulation_id}")
def get_status(simulation_id: str):
    """
    Retrieve the status of a simulation
    """
    from utils import fetch_job_status

    status, result = fetch_job_status(simulation_id)
    if not isinstance(status, str):
        return status

    return {"status": status,
            "result": result}


@app.post("/mathml_to_amr")
def mathml_to_amr(payload: List[str], model: str = "petrinet"):
    """Post MathML to skema service to get AMR return

    Args:
        payload (List[str]): A list of MathML strings representing the functions that are used to convert to AMR
        model (str, optional): AMR model return type. Defaults to "petrinet". Options: "regnet", "petrinet".
    """
    from utils import create_job

    operation_name="operations.put_mathml_to_skema"
    options = {
        "mathml": payload,
        "model": model
    }

    resp = create_job(operation_name=operation_name, options=options)

    # response = {"simulation_id": resp["id"]}

    return resp

@app.post("/pdf_extractions")
async def pdf_extractions(pdf: UploadFile = File(...), annotate_skema: bool = True, annotate_mit: bool = True):
    """Run text extractions over pdfs

    Args:
        pdf (UploadFile, optional): The pdf to run extractions over. Defaults to File(...).
    """

    from utils import create_job

    # Create an in-memory file-like object from the binary content    
    filename = pdf.filename
    pdf_file = io.BytesIO(await pdf.read())

    if filename.split('.')[-1] == "pdf":

        # Open the PDF file and extract text content
        pdf_reader = pypdf.PdfReader(pdf_file)
        num_pages = len(pdf_reader.pages)

        text_content = ""
        for page_number in range(num_pages):
            page = pdf_reader.pages[page_number]
            text_content += page.extract_text()
    else:

        # Open the TXT file and extract text content
        with pdf_file as pdf:
            text_content = ""
            for page in pdf:
                text_content += page.decode("utf-8")

    operation_name="operations.pdf_extractions"
    options = {
        "text_content": text_content,
        "annotate_skema": annotate_skema,
        "annotate_mit": annotate_mit
    }

    resp = create_job(operation_name=operation_name, options=options)

    return resp
