from pydantic import BaseModel


class ValidationRequest(BaseModel):
    resource: dict
    profile: str | None = None
    fhir_version: str | None = None


class ValidationIssue(BaseModel):
    severity: str
    path: str
    message: str


class ValidationResponse(BaseModel):
    valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
