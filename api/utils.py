# WIP
from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from ast import Dict
from copy import deepcopy
from typing import Any, Optional

from fastapi import Response, status
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from api.models import ExtractionJob

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # default to INFO if not set
numeric_level = getattr(logging, LOG_LEVEL, None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {LOG_LEVEL}")
logging.basicConfig()
logging.getLogger().setLevel(numeric_level)

# REDIS CONNECTION AND QUEUE OBJECTS
def get_redis():
    redis = Redis(
        os.environ.get("REDIS_HOST", "redis.ta1-service"),
        os.environ.get("REDIS_PORT", "6379"),
    )


def create_job(operation_name: str, options: Optional[Dict[Any, Any]] = None, *, redis):
    q = Queue(connection=redis, default_timeout=-1)

    if options is None:
        options = {}

    force_restart = options.pop("force_restart", False)
    synchronous = options.pop("synchronous", False)
    timeout = options.pop("timeout", 60)
    recheck_delay = 0.5

    random_id = str(uuid.uuid4())

    job_id = f"extraction-{random_id}"
    options["job_id"] = job_id
    job = q.fetch_job(job_id)

    if job and force_restart:
        job.cleanup(ttl=0)  # Cleanup/remove data immediately

    if not job or force_restart:
        flattened_options = deepcopy(options)
    job = q.enqueue_call(
        func=f"worker.{operation_name}", args=[], kwargs=flattened_options, job_id=job_id
    )
    if synchronous:
        timer = 0.0
        while (
            job.get_status(refresh=True) not in ("finished", "failed")
            and timer < timeout
        ):
            time.sleep(recheck_delay)
            timer += recheck_delay

    status = job.get_status()
    if status in ("finished", "failed"):
        job_result = job.return_value()
        job_error = job.exc_info
        job.cleanup(ttl=0)  # Cleanup/remove data immediately
    else:
        job_result = None
        job_error = None

    result = {
        "created_at": job.created_at,
        "enqueued_at": job.enqueued_at,
        "started_at": job.started_at,
        "job_error": job_error,
        "job_result": job_result,
    }
    return ExtractionJob(id=job_id, status=status, result=result)


def fetch_job_status(job_id, redis):
    """Fetch a job's results from RQ.

    Args:
        job_id (str): The id of the job being run in RQ. Comes from the job/enqueue/{operation_name} endpoint.

    Returns:
        Response:
            status_code: 200 if successful, 404 if job does not exist.
            content: contains the job's results.
    """
    try:
        job = Job.fetch(job_id, connection=redis)
        result = {
            "created_at": job.created_at,
            "enqueued_at": job.enqueued_at,
            "started_at": job.started_at,
            "job_error": job.exc_info,
            "job_result": job.return_value(),
        }
        return ExtractionJob(id=job_id, status=job.get_status(), result=result)
    except NoSuchJobError:
        return status.HTTP_404_NOT_FOUND
