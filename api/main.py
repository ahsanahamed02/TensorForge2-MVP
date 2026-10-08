import os
import json
import uuid
import time
import hmac
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from model.predictor import predict_ticket
from fastapi.middleware.cors import CORSMiddleware
# =========================================================
# CONFIG
# =========================================================
MODEL_VERSION = "v1.0"
PREDICT_MAX_BYTES = 1 * 1024 * 1024
BATCH_MAX_BYTES = 5 * 1024 * 1024
JOB_MAX_BYTES = 25 * 1024 * 1024
MAX_RUNNING_JOBS = 1
MAX_QUEUED_JOBS = 3
RETRY_AFTER = 3
RETENTION_HOURS = 6
BASE_DIR = Path(__file__).resolve().parent
JOB_DIR = BASE_DIR / "job_data"
JOB_DIR.mkdir(parents=True, exist_ok=True)
job_lock = threading.Lock()
worker_lock = threading.Lock()
# =========================================================
# FASTAPI
# =========================================================
app = FastAPI(
    title="TensorForge 2.0 - RouteIQ API",
    version=MODEL_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# OPENAPI DOCUMENTATION SCHEMAS
# =========================================================
TICKET_SCHEMA = {
    "type": "object",
    "required": [
        "ticket_id",
        "channel",
        "text"
    ],
    "properties": {
        "ticket_id": {
            "type": "string",
            "maxLength": 64,
            "example": "JOB-001"
        },
        "channel": {
            "type": "string",
            "enum": [
                "email",
                "chat",
                "call_transcript"
            ],
            "example": "email"
        },
        "subject": {
            "type": "string",
            "maxLength": 500,
            "default": "",
            "example": "Refund problem"
        },
        "text": {
            "type": "string",
            "minLength": 1,
            "maxLength": 10000,
            "example": (
                "I was charged twice for my order. "
                "Please refund the extra payment."
            )
        }
    }
}
SINGLE_TICKET_SCHEMA = {
    "type": "object",
    "required": [
        "channel",
        "text"
    ],
    "properties": {
        "ticket_id": {
            "type": "string",
            "maxLength": 64,
            "example": "TEST-001"
        },
        "channel": {
            "type": "string",
            "enum": [
                "email",
                "chat",
                "call_transcript"
            ],
            "example": "email"
        },
        "subject": {
            "type": "string",
            "maxLength": 500,
            "default": "",
            "example": "Refund problem"
        },
        "text": {
            "type": "string",
            "minLength": 1,
            "maxLength": 10000,
            "example": (
                "I was charged twice for my order."
            )
        }
    }
}
SYNC_BATCH_SCHEMA = {
    "type": "object",
    "required": ["tickets"],
    "properties": {
        "tickets": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": TICKET_SCHEMA
        }
    }
}
ASYNC_BATCH_SCHEMA = {
    "type": "object",
    "required": ["tickets"],
    "properties": {
        "tickets": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5000,
            "items": TICKET_SCHEMA
        }
    }
}
PREDICTION_SCHEMA = {
    "type": "object",
    "required": [
        "category",
        "secondary_category",
        "team",
        "is_urgent",
        "confidence",
        "model_version"
    ],
    "properties": {
        "ticket_id": {
            "type": "string",
            "nullable": True
        },
        "category": {
            "type": "string"
        },
        "secondary_category": {
            "type": "string",
            "nullable": True
        },
        "team": {
            "type": "string"
        },
        "is_urgent": {
            "type": "boolean"
        },
        "confidence": {
            "type": "number"
        },
        "model_version": {
            "type": "string"
        }
    }
}
SYNC_BATCH_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["predictions", "meta"],
    "properties": {
        "predictions": {
            "type": "array",
            "items": PREDICTION_SCHEMA
        },
        "meta": {
            "type": "object",
            "required": ["count", "model_version", "processing_time_ms"],
            "properties": {
                "count": {"type": "integer"},
                "model_version": {"type": "string"},
                "processing_time_ms": {"type": "integer"}
            }
        }
    }
}
JOB_STATUS_SCHEMA = {
    "type": "object",
    "required": [
        "job_id",
        "status",
        "total",
        "processed",
        "model_version"
    ],
    "properties": {
        "job_id": {
            "type": "string"
        },
        "status": {
            "type": "string",
            "enum": [
                "queued",
                "running",
                "succeeded",
                "failed",
                "cancelled"
            ]
        },
        "total": {
            "type": "integer"
        },
        "processed": {
            "type": "integer"
        },
        "created_at": {
            "type": "string",
            "nullable": True
        },
        "started_at": {
            "type": "string",
            "nullable": True
        },
        "finished_at": {
            "type": "string",
            "nullable": True
        },
        "expires_at": {
            "type": "string",
            "nullable": True
        },
        "model_version": {
            "type": "string"
        },
        "error": {
            "type": "object",
            "nullable": True,
            "required": ["code", "message"],
            "properties": {
                "code": {"type": "string"},
                "message": {"type": "string"}
            }
        }
    }
}
JOB_RESULTS_SCHEMA = {
    "type": "object",
    "required": [
        "job_id",
        "status",
        "total",
        "offset",
        "limit",
        "model_version",
        "predictions"
    ],
    "properties": {
        "job_id": {
            "type": "string"
        },
        "status": {
            "type": "string",
            "enum": ["succeeded"]
        },
        "total": {
            "type": "integer"
        },
        "offset": {
            "type": "integer"
        },
        "limit": {
            "type": "integer"
        },
        "next_offset": {
            "type": "integer",
            "nullable": True
        },
        "model_version": {
            "type": "string"
        },
        "predictions": {
            "type": "array",
            "items": PREDICTION_SCHEMA
        }
    }
}
ERROR_SCHEMA = {
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {
            "type": "object",
            "required": [
                "code",
                "message"
            ],
            "properties": {
                "code": {
                    "type": "string"
                },
                "message": {
                    "type": "string"
                },
                "details": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            }
        }
    }
}
COMMON_ERROR_RESPONSES = {
    401: {
        "description": "API key missing or invalid",
        "content": {
            "application/json": {
                "schema": ERROR_SCHEMA
            }
        }
    },
    404: {
        "description": "No job with this id",
        "content": {
            "application/json": {
                "schema": ERROR_SCHEMA
            }
        }
    },
    409: {
        "description": "Job is not ready",
        "content": {
            "application/json": {
                "schema": ERROR_SCHEMA
            }
        }
    },
    410: {
        "description": "Job results have expired",
        "content": {
            "application/json": {
                "schema": ERROR_SCHEMA
            }
        }
    },
    422: {
        "description": "Request failed validation",
        "content": {
            "application/json": {
                "schema": ERROR_SCHEMA
            }
        }
    },
}
# =========================================================
# GENERAL HELPERS
# =========================================================
def utc_now():
    return datetime.now(timezone.utc)
def iso_time(value=None):
    if value is None:
        value = utc_now()
    return (
        value.isoformat()
        .replace("+00:00", "Z")
    )
def error_response(
    status_code,
    code,
    message,
    details=None,
    headers=None
):
    body = {
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        body["error"]["details"] = details
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers=headers or {}
    )
def request_id_headers(request: Request):
    request_id = request.headers.get(
        "X-Request-ID"
    )
    if request_id:
        return {
            "X-Request-ID":
                request_id[:128]
        }
    return {}
# =========================================================
# AUTHENTICATION
# =========================================================
def check_auth(request: Request):
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        return error_response(
            401,
            "unauthorized",
            (
                "Missing API key. Send "
                "X-API-Key or Authorization Bearer."
            ),
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )
    supplied_key = request.headers.get(
        "X-API-Key"
    )
    if not supplied_key:
        authorization = request.headers.get(
            "Authorization",
            ""
        )
        if authorization.startswith(
            "Bearer "
        ):
            supplied_key = authorization[7:]
    if not supplied_key:
        return error_response(
            401,
            "unauthorized",
            (
                "Missing API key. Send "
                "X-API-Key or Authorization Bearer."
            ),
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )
    if not hmac.compare_digest(
        supplied_key,
        expected_key
    ):
        return error_response(
            401,
            "unauthorized",
            "Invalid API key.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )
    return None
# =========================================================
# BODY READING
# =========================================================
async def read_json_body(
    request: Request,
    max_bytes: int
):
    # 1. Authentication
    auth_error = check_auth(request)
    if auth_error:
        return None, auth_error
    # 2. Content-Type
    content_type = request.headers.get(
        "content-type",
        ""
    )
    if not content_type.lower().startswith(
        "application/json"
    ):
        return None, error_response(
            415,
            "unsupported_media_type",
            (
                "Content-Type must be "
                "application/json."
            )
        )
    # 3. Content-Length
    content_length = request.headers.get(
        "content-length"
    )
    if content_length:
        try:
            if int(content_length) > max_bytes:
                return None, error_response(
                    413,
                    "payload_too_large",
                    (
                        "Request body exceeds "
                        "the maximum allowed size."
                    )
                )
        except ValueError:
            pass
    # 4. Read actual body
    raw = await request.body()
    if len(raw) > max_bytes:
        return None, error_response(
            413,
            "payload_too_large",
            (
                "Request body exceeds "
                "the maximum allowed size."
            )
        )
    # 5. JSON parsing
    try:
        data = json.loads(raw)
    except Exception:
        return None, error_response(
            400,
            "malformed_json",
            "Request body is not valid JSON."
        )
    return data, None
# =========================================================
# TICKET VALIDATION
# =========================================================
def validate_ticket(
    data,
    require_ticket_id=False
):
    details = []
    if not isinstance(data, dict):
        return None, [
            {
                "field": "ticket",
                "issue": "must be an object"
            }
        ]
    # ticket_id
    if require_ticket_id:
        if "ticket_id" not in data:
            details.append({
                "field": "ticket_id",
                "issue": "is required"
            })
        elif not isinstance(
            data.get("ticket_id"),
            str
        ):
            details.append({
                "field": "ticket_id",
                "issue": "must be a string"
            })
        elif len(data["ticket_id"]) < 1:
            details.append({
                "field": "ticket_id",
                "issue": "must not be empty"
            })
        elif len(data["ticket_id"]) > 64:
            details.append({
                "field": "ticket_id",
                "issue": (
                    "must be at most "
                    "64 characters"
                )
            })

    elif "ticket_id" in data:
        if not isinstance(
            data["ticket_id"],
            str
        ):
            details.append({
                "field": "ticket_id",
                "issue": "must be a string"
            })
        elif len(data["ticket_id"]) > 64:
            details.append({
                "field": "ticket_id",
                "issue": (
                    "must be at most "
                    "64 characters"
                )
            })
    # channel
    channel = data.get("channel")
    if channel is None:
        details.append({
            "field": "channel",
            "issue": "is required"
        })
    elif not isinstance(channel, str):
        details.append({
            "field": "channel",
            "issue": "must be a string"
        })
    elif channel not in [
        "email",
        "chat",
        "call_transcript"
    ]:
        details.append({
            "field": "channel",
            "issue": (
                "must be one of email, "
                "chat, call_transcript"
            )
        })
    # subject
    subject = data.get(
        "subject",
        ""
    )
    if not isinstance(subject, str):
        details.append({
            "field": "subject",
            "issue": "must be a string"
        })
    elif len(subject) > 500:
        details.append({
            "field": "subject",
            "issue": (
                "must be at most "
                "500 characters"
            )
        })
    # text
    if "text" not in data:
        details.append({
            "field": "text",
            "issue": "is required"
        })
    else:
        text = data["text"]
        if not isinstance(text, str):
            details.append({
                "field": "text",
                "issue": "must be a string"
            })
        elif len(text) > 10000:
            details.append({
                "field": "text",
                "issue": (
                    "must be at most "
                    "10000 characters"
                )
            })
        elif not text.strip():
            details.append({
                "field": "text",
                "issue": (
                    "must contain at least one "
                    "non-whitespace character"
                )
            })
    if details:
        return None, details
    ticket = {
        "channel": channel,
        "subject": subject,
        "text": data["text"]
    }
    if data.get("ticket_id") is not None:
        ticket["ticket_id"] = (
            data["ticket_id"]
        )
    return ticket, []
# =========================================================
# BATCH VALIDATION
# =========================================================
def validate_batch(
    data,
    max_items
):
    if not isinstance(data, dict):
        return None, [
            {
                "field": "tickets",
                "issue": "is required"
            }
        ]
    tickets = data.get("tickets")
    if not isinstance(tickets, list):
        return None, [
            {
                "field": "tickets",
                "issue": "must be an array"
            }
        ]
    if (
        len(tickets) < 1
        or len(tickets) > max_items
    ):
        return None, [
            {
                "field": "tickets",
                "issue": (
                    f"must contain between "
                    f"1 and {max_items} items"
                )
            }
        ]
    valid_tickets = []
    details = []
    seen_ids = set()
    for index, item in enumerate(tickets):
        ticket, ticket_errors = (
            validate_ticket(
                item,
                require_ticket_id=True
            )
        )
        for problem in ticket_errors:
            problem = dict(problem)
            problem["index"] = index
            details.append(problem)
        if ticket is not None:
            ticket_id = ticket["ticket_id"]
            if ticket_id in seen_ids:
                details.append({
                    "index": index,
                    "field": "ticket_id",
                    "issue": (
                        "duplicate of an "
                        "earlier item"
                    )
                })
            else:
                seen_ids.add(ticket_id)
            valid_tickets.append(ticket)
    if details:
        return None, details
    return valid_tickets, []
# =========================================================
# MODEL PREDICTION
# =========================================================
def make_prediction(ticket):
    result = predict_ticket(
        channel=ticket["channel"],
        subject=ticket.get(
            "subject",
            ""
        ),
        text=ticket["text"]
    )
    if "ticket_id" in ticket:
        result["ticket_id"] = (
            ticket["ticket_id"]
        )
    return result
# =========================================================
# JOB STORAGE
# =========================================================
def job_path(job_id):
    return JOB_DIR / f"{job_id}.json"
def load_job(job_id):
    path = job_path(job_id)
    if not path.exists():
        return None
    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)
    except Exception:
        return None
def save_job(job):
    path = job_path(
        job["job_id"]
    )
    temp_path = path.with_suffix(
        ".tmp"
    )
    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            job,
            file,
            ensure_ascii=False
        )
    temp_path.replace(path)
def delete_job_file(job_id):
    path = job_path(job_id)
    if path.exists():
        path.unlink()
def all_jobs():
    jobs = []
    for path in JOB_DIR.glob("*.json"):
        try:
            with open(
                path,
                "r",
                encoding="utf-8"
            ) as file:
                jobs.append(
                    json.load(file)
                )
        except Exception:
            continue
    return jobs
# =========================================================
# JOB EXPIRATION
# =========================================================
def is_expired(job):
    expires_at = job.get(
        "expires_at"
    )
    if not expires_at:
        return False
    try:
        expiry = datetime.fromisoformat(
            expires_at.replace(
                "Z",
                "+00:00"
            )
        )
        return utc_now() >= expiry
    except Exception:
        return False
# =========================================================
# PUBLIC JOB RESPONSE
# =========================================================
def public_job_status(job):
    return {
        "job_id":
            job["job_id"],
        "status":
            job["status"],
        "total":
            job["total"],
        "processed":
            job["processed"],
        "created_at":
            job.get("created_at"),
        "started_at":
            job.get("started_at"),
        "finished_at":
            job.get("finished_at"),
        "expires_at":
            job.get("expires_at"),
        "model_version":
            MODEL_VERSION,
        "error":
            job.get("error")
    }
# =========================================================
# JOB COUNTS
# =========================================================
def active_job_counts():
    running = 0
    queued = 0
    for job in all_jobs():
        if job.get("status") == "running":
            running += 1
        elif job.get("status") == "queued":
            queued += 1
    return running, queued
# =========================================================
# IDEMPOTENCY
# =========================================================
def find_by_idempotency_key(key):
    if not key:
        return None
    for job in all_jobs():
        if (
            job.get(
                "idempotency_key"
            )
            == key
        ):
            return job
    return None
# =========================================================
# RESTART RECOVERY
# =========================================================
def recover_interrupted_jobs():
    with job_lock:
        for job in all_jobs():
            if (
                job.get("status")
                == "running"
            ):
                finished = utc_now()
                job["status"] = "failed"
                job["finished_at"] = (
                    iso_time(finished)
                )
                job["expires_at"] = (
                    iso_time(
                        finished
                        + timedelta(
                            hours=
                                RETENTION_HOURS
                        )
                    )
                )
                job["error"] = {
                    "code": "interrupted",
                    "message": (
                        "Service restarted while "
                        "the job was running."
                    )
                }
                save_job(job)
recover_interrupted_jobs()
# =========================================================
# BACKGROUND WORKER
# =========================================================
def run_job(job_id):
    with worker_lock:
        with job_lock:
            job = load_job(job_id)
            if not job:
                return
            if (
                job["status"]
                == "cancelled"
            ):
                return
            job["status"] = "running"
            job["started_at"] = iso_time()
            save_job(job)
        try:
            predictions = []
            tickets = job["tickets"]
            for index, ticket in enumerate(
                tickets
            ):
                with job_lock:
                    latest = load_job(
                        job_id
                    )
                    if not latest:
                        return
                    if (
                        latest["status"]
                        == "cancelled"
                    ):
                        return
                result = make_prediction(
                    ticket
                )
                predictions.append(
                    result
                )
                with job_lock:
                    latest = load_job(
                        job_id
                    )
                    if not latest:
                        return
                    if (
                        latest["status"]
                        == "cancelled"
                    ):
                        return
                    latest["processed"] = (
                        index + 1
                    )
                    latest[
                        "predictions"
                    ] = predictions
                    save_job(latest)
            finished = utc_now()
            with job_lock:
                latest = load_job(
                    job_id
                )
                if not latest:
                    return
                if (
                    latest["status"]
                    == "cancelled"
                ):
                    return
                latest["status"] = (
                    "succeeded"
                )
                latest["processed"] = (
                    latest["total"]
                )
                latest[
                    "predictions"
                ] = predictions
                latest["finished_at"] = (
                    iso_time(finished)
                )
                latest["expires_at"] = (
                    iso_time(
                        finished
                        + timedelta(
                            hours=
                                RETENTION_HOURS
                        )
                    )
                )
                latest["error"] = None
                save_job(latest)
        except Exception:
            finished = utc_now()
            with job_lock:
                latest = load_job(
                    job_id
                )
                if latest:
                    latest["status"] = (
                        "failed"
                    )
                    latest[
                        "finished_at"
                    ] = iso_time(
                        finished
                    )
                    latest[
                        "expires_at"
                    ] = iso_time(
                        finished
                        + timedelta(
                            hours=
                                RETENTION_HOURS
                        )
                    )
                    latest["error"] = {
                        "code":
                            "processing_error",
                        "message": (
                            "The batch job could "
                            "not be completed."
                        )
                    }
                    save_job(latest)
        finally:
            start_next_queued_job()
def start_job_thread(job_id):
    thread = threading.Thread(
        target=run_job,
        args=(job_id,),
        daemon=True
    )
    thread.start()
def start_next_queued_job():
    with job_lock:
        running, _ = (
            active_job_counts()
        )
        if (
            running
            >= MAX_RUNNING_JOBS
        ):
            return
        queued_jobs = [
            job
            for job in all_jobs()
            if (
                job.get("status")
                == "queued"
            )
        ]
        if not queued_jobs:
            return
        queued_jobs.sort(
            key=lambda item:
                item["created_at"]
        )
        next_job = queued_jobs[0]
    start_job_thread(
        next_job["job_id"]
    )
# =========================================================
# HEALTH
# =========================================================
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
        "model_loaded": True
    }
# =========================================================
# SINGLE PREDICT
# =========================================================
@app.post(
    "/predict",
    responses={
        200: {
            "description": "Successful Response",
            "content": {"application/json": {"schema": PREDICTION_SCHEMA}}
        }
    },
    openapi_extra={
        "parameters": [
            {
                "name": "X-API-Key",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            }
        ],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema":
                        SINGLE_TICKET_SCHEMA
                }
            }
        }
    }
)
async def predict(
    request: Request
):
    data, body_error = (
        await read_json_body(
            request,
            PREDICT_MAX_BYTES
        )
    )
    if body_error:
        return body_error
    ticket, details = validate_ticket(
        data,
        require_ticket_id=False
    )
    if details:
        return error_response(
            422,
            "validation_error",
            "Request failed validation.",
            details
        )
    result = make_prediction(ticket)
    return JSONResponse(
        status_code=200,
        content=result,
        headers=request_id_headers(
            request
        )
    )
# =========================================================
# SYNCHRONOUS BATCH
# =========================================================
@app.post(
    "/predict/batch",
    responses={
        200: {
            "description": "Successful Response",
            "content": {"application/json": {"schema": SYNC_BATCH_RESPONSE_SCHEMA}}
        }
    },
    openapi_extra={
        "parameters": [
            {
                "name": "X-API-Key",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            }
        ],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema":
                        SYNC_BATCH_SCHEMA
                }
            }
        }
    }
)
async def predict_batch(
    request: Request
):
    data, body_error = (
        await read_json_body(
            request,
            BATCH_MAX_BYTES
        )
    )
    if body_error:
        return body_error
    tickets, details = validate_batch(
        data,
        100
    )
    if details:
        return error_response(
            422,
            "validation_error",
            "Request failed validation.",
            details
        )
    start = time.perf_counter()
    predictions = [
        make_prediction(ticket)
        for ticket in tickets
    ]
    processing_time_ms = int(
        (
            time.perf_counter()
            - start
        )
        * 1000
    )
    body = {
        "predictions":
            predictions,
        "meta": {
            "count":
                len(predictions),
            "model_version":
                MODEL_VERSION,
            "processing_time_ms":
                processing_time_ms
        }
    }
    return JSONResponse(
        status_code=200,
        content=body,
        headers=request_id_headers(
            request
        )
    )
# =========================================================
# CREATE ASYNC JOB
# =========================================================
@app.post(
    "/batch/jobs",
    status_code=202,
    responses={
        202: {
            "description": "Batch job accepted",
            "content": {
                "application/json": {
                    "schema": JOB_STATUS_SCHEMA
                }
            }
        }
    },
    openapi_extra={
        "parameters": [
            {
                "name": "X-API-Key",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string",
                    "maxLength": 128
                }
            }
        ],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema":
                        ASYNC_BATCH_SCHEMA,
                    "example": {
                        "tickets": [
                            {
                                "ticket_id":
                                    "JOB-001",
                                "channel":
                                    "email",
                                "subject":
                                    "Refund problem",
                                "text": (
                                    "I was charged "
                                    "twice for my order."
                                )
                            },
                            {
                                "ticket_id":
                                    "JOB-002",
                                "channel":
                                    "chat",
                                "subject":
                                    "Late delivery",
                                "text": (
                                    "My food delivery "
                                    "has not arrived."
                                )
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def create_batch_job(
    request: Request
):
    data, body_error = (
        await read_json_body(
            request,
            JOB_MAX_BYTES
        )
    )
    if body_error:
        return body_error
    tickets, details = validate_batch(
        data,
        5000
    )
    if details:
        return error_response(
            422,
            "validation_error",
            "Request failed validation.",
            details
        )
    idempotency_key = (
        request.headers.get(
            "Idempotency-Key"
        )
    )
    if (
        idempotency_key
        and len(idempotency_key) > 128
    ):
        return error_response(
            422,
            "validation_error",
            "Request failed validation.",
            [
                {
                    "field":
                        "Idempotency-Key",
                    "issue": (
                        "must be at most "
                        "128 characters"
                    )
                }
            ]
        )
    with job_lock:
        existing = (
            find_by_idempotency_key(
                idempotency_key
            )
        )
        if existing:
            headers = {
                "Location": (
                    f"/batch/jobs/"
                    f"{existing['job_id']}"
                ),
                "Retry-After":
                    str(RETRY_AFTER)
            }
            headers.update(
                request_id_headers(
                    request
                )
            )
            return JSONResponse(
                status_code=202,
                content=public_job_status(
                    existing
                ),
                headers=headers
            )
        running, queued = (
            active_job_counts()
        )
        if (
            running
            >= MAX_RUNNING_JOBS
            and
            queued
            >= MAX_QUEUED_JOBS
        ):
            return error_response(
                429,
                "too_many_jobs",
                (
                    "Job queue is full. "
                    "Retry later."
                ),
                headers={
                    "Retry-After":
                        str(RETRY_AFTER)
                }
            )
        job_id = str(
            uuid.uuid4()
        )
        job = {
            "job_id":
                job_id,
            "status":
                "queued",
            "total":
                len(tickets),
            "processed":
                0,
            "created_at":
                iso_time(),
            "started_at":
                None,
            "finished_at":
                None,
            "expires_at":
                None,
            "model_version":
                MODEL_VERSION,
            "error":
                None,
            "tickets":
                tickets,
            "predictions":
                [],
            "idempotency_key":
                idempotency_key
        }
        save_job(job)
        should_start = (
            running
            < MAX_RUNNING_JOBS
        )
    if should_start:
        start_job_thread(
            job_id
        )
    headers = {
        "Location":
            f"/batch/jobs/{job_id}",
        "Retry-After":
            str(RETRY_AFTER)
    }
    headers.update(
        request_id_headers(
            request
        )
    )
    return JSONResponse(
        status_code=202,
        content=public_job_status(
            job
        ),
        headers=headers
    )
# =========================================================
# GET JOB STATUS
# =========================================================
@app.get(
    "/batch/jobs/{job_id}",
        responses={
            200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "schema": JOB_STATUS_SCHEMA
                }
            }
        },
        401: COMMON_ERROR_RESPONSES[401],
        404: COMMON_ERROR_RESPONSES[404],
        410: COMMON_ERROR_RESPONSES[410],
    },
    openapi_extra={
        "parameters": [
            {
                "name": "X-API-Key",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            }
        ]
    }
)
async def get_batch_job(
    job_id: str,
    request: Request
):
    auth_error = check_auth(
        request
    )
    if auth_error:
        return auth_error
    with job_lock:
        job = load_job(job_id)
    if not job:
        return error_response(
            404,
            "job_not_found",
            "No job with this id."
        )
    if is_expired(job):
        return error_response(
            410,
            "job_expired",
            "Job results have expired."
        )
    headers = request_id_headers(
        request
    )
    if job["status"] in [
        "queued",
        "running"
    ]:
        headers["Retry-After"] = (
            str(RETRY_AFTER)
        )
    return JSONResponse(
        status_code=200,
        content=public_job_status(
            job
        ),
        headers=headers
    )
# =========================================================
# GET JOB RESULTS
# =========================================================
@app.get(
    "/batch/jobs/{job_id}/results",
     responses={
         200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "schema": JOB_RESULTS_SCHEMA
                }
            }
        },
        401: COMMON_ERROR_RESPONSES[401],
        404: COMMON_ERROR_RESPONSES[404],
        409: COMMON_ERROR_RESPONSES[409],
        410: COMMON_ERROR_RESPONSES[410],
        422: COMMON_ERROR_RESPONSES[422],
    },
    openapi_extra={
        "parameters": [
            {
                "name": "X-API-Key",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            }
        ]
    }
)
async def get_batch_job_results(
    job_id: str,
    request: Request,
    offset: int = 0,
    limit: Optional[int] = None
):
    auth_error = check_auth(
        request
    )
    if auth_error:
        return auth_error
    if offset < 0:
        return error_response(
            422,
            "validation_error",
            "Request failed validation.",
            [
                {
                    "field": "offset",
                    "issue": (
                        "must be greater than "
                        "or equal to 0"
                    )
                }
            ]
        )
    if limit is not None:
        if (
            limit < 1
            or limit > 5000
        ):
            return error_response(
                422,
                "validation_error",
                "Request failed validation.",
                [
                    {
                        "field":
                            "limit",
                        "issue": (
                            "must be between "
                            "1 and 5000"
                        )
                    }
                ]
            )
    with job_lock:
        job = load_job(job_id)
    if not job:
        return error_response(
            404,
            "job_not_found",
            "No job with this id."
        )
    if is_expired(job):
        return error_response(
            410,
            "job_expired",
            "Job results have expired."
        )
    if (
        job["status"]
        != "succeeded"
    ):
        return error_response(
            409,
            "job_not_ready",
            (
                f"Job status is "
                f"'{job['status']}'. "
                f"Results are available "
                f"once it is 'succeeded'."
            )
        )
    predictions = job.get(
        "predictions",
        []
    )
    total = len(predictions)
    if limit is None:
        limit = min(
            5000,
            max(
                1,
                total - offset
            )
        )
    page = predictions[
        offset:offset + limit
    ]
    next_offset = (
        offset + len(page)
    )
    if next_offset >= total:
        next_offset = None
    body = {
        "job_id":
            job_id,
        "status":
            "succeeded",
        "total":
            total,
        "offset":
            offset,
        "limit":
            limit,
        "next_offset":
            next_offset,
        "model_version":
            MODEL_VERSION,
        "predictions":
            page
    }
    return JSONResponse(
        status_code=200,
        content=body,
        headers=request_id_headers(
            request
        )
    )
# =========================================================
# DELETE / CANCEL JOB
# =========================================================
@app.delete(
    "/batch/jobs/{job_id}",
    status_code=204,
     responses={
        401: COMMON_ERROR_RESPONSES[401],
        404: COMMON_ERROR_RESPONSES[404],
    },
    openapi_extra={
        "parameters": [
            {
                "name": "X-API-Key",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "Authorization",
                "in": "header",
                "required": False,
                "schema": {
                    "type": "string"
                }
            }
        ]
    }
)
async def delete_batch_job(
    job_id: str,
    request: Request
):
    auth_error = check_auth(request)
    if auth_error:
        return auth_error
    with job_lock:
        job = load_job(job_id)
        if not job:
            return error_response(
                404,
                "job_not_found",
                "No job with this id."
            )
        # Remove the job completely.
        # Any later request using this job_id
        # must therefore return 404.
        delete_job_file(job_id)
    # If a running/queued job was removed,
    # allow the next queued job to start.
    start_next_queued_job()
    return Response(
        status_code=204,
        headers=request_id_headers(request)
    )
# =========================================================
# JSON 404 / 405
# =========================================================
@app.exception_handler(404)
async def not_found_handler(
    request: Request,
    exc
):
    return error_response(
        404,
        "not_found",
        "Route not found."
    )
@app.exception_handler(405)
async def method_not_allowed_handler(
    request: Request,
    exc
):
    return error_response(
        405,
        "method_not_allowed",
        "Method not allowed."
    )
