from __future__ import annotations

from typing import List

from fastapi import FastAPI, Response, status
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
    """# Post MathML to skema service to get AMR return

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




