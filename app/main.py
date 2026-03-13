import json
import os

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.responses import JSONResponse

from app.auth import verify_api_key
from app.config import settings
from app.models import ValidationResponse
from app.validator import run_validation

app = FastAPI(
    title="FHIR Validator API",
    description="REST API for validating FHIR R4 resources using the HAPI FHIR validator",
    version="1.0.0",
)


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    max_bytes = settings.max_request_size_mb * 1024 * 1024
    if content_length and int(content_length) > max_bytes:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request body exceeds {settings.max_request_size_mb}MB limit"},
        )
    return await call_next(request)


@app.get("/health")
async def health():
    jar_exists = os.path.isfile(settings.validator_jar_path)
    return {
        "status": "ok" if jar_exists else "degraded",
        "validator_jar_found": jar_exists,
        "fhir_version": settings.fhir_version,
    }


@app.post("/validate", response_model=ValidationResponse)
async def validate(
    request: Request,
    profile: str | None = Query(default=None, description="FHIR StructureDefinition URL to validate against"),
    fhir_version: str | None = Query(default=None, description="FHIR version override (default: 4.0.1)"),
    content_type: str | None = Header(default=None, alias="content-type"),
    _api_key: str = Depends(verify_api_key),
):
    body = await request.body()
    if not body:
        return JSONResponse(status_code=400, content={"detail": "Empty request body"})

    raw = body.decode("utf-8")

    # Detect format from Content-Type header
    if content_type and "xml" in content_type:
        content_format = "xml"
        content = raw
    else:
        # Default: JSON — accept both raw FHIR JSON and wrapped {"resource": ...} format
        content_format = "json"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})

        # Support wrapped format: {"resource": {...}, "profile": "...", "fhir_version": "..."}
        if "resource" in parsed and isinstance(parsed["resource"], dict):
            content = json.dumps(parsed["resource"])
            if not profile and parsed.get("profile"):
                profile = parsed["profile"]
            if not fhir_version and parsed.get("fhir_version"):
                fhir_version = parsed["fhir_version"]
        else:
            # Assume raw FHIR resource JSON
            content = raw

    return run_validation(
        content=content,
        content_format=content_format,
        profile=profile,
        fhir_version=fhir_version,
    )
