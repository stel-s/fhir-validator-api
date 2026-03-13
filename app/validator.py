import json
import subprocess
import tempfile

from app.config import settings
from app.models import ValidationIssue, ValidationResponse


def run_validation(
    content: str,
    content_format: str = "json",
    profile: str | None = None,
    fhir_version: str | None = None,
) -> ValidationResponse:
    version = fhir_version or settings.fhir_version
    suffix = ".xml" if content_format == "xml" else ".json"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    cmd = [
        "java",
        "-jar",
        settings.validator_jar_path,
        tmp_path,
        "-version",
        version,
        "-output-style",
        "json",
    ]

    if profile:
        cmd.extend(["-profile", profile])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.validator_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return ValidationResponse(
            valid=False,
            errors=[
                ValidationIssue(
                    severity="fatal",
                    path="(root)",
                    message=f"Validation timed out after {settings.validator_timeout_seconds}s",
                )
            ],
            warnings=[],
        )

    return _parse_output(result.stdout, result.stderr, result.returncode)


def _extract_json(text: str) -> dict | None:
    """Extract the JSON OperationOutcome block from validator output mixed with log lines."""
    # Find the first '{' that starts the JSON object
    start = text.find('{\n  "resourceType"')
    if start == -1:
        start = text.find('{"resourceType"')
    if start == -1:
        return None

    # Find the matching closing brace by counting braces
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _parse_output(
    stdout: str, stderr: str, returncode: int
) -> ValidationResponse:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    # Try to extract and parse the JSON OperationOutcome from stdout
    data = _extract_json(stdout)
    try:
        if data is None:
            raise ValueError("No JSON found")
        issues = data.get("issue", [])
        for issue in issues:
            severity = issue.get("severity", "error")
            path = (
                issue.get("expression", [None])[0]
                if issue.get("expression")
                else issue.get("location", [None])[0]
                if issue.get("location")
                else "(unknown)"
            )
            message = issue.get("diagnostics", issue.get("details", {}).get("text", "No details"))

            item = ValidationIssue(
                severity=severity,
                path=path or "(unknown)",
                message=message,
            )

            if severity in ("error", "fatal"):
                errors.append(item)
            elif severity == "warning":
                warnings.append(item)
            # information-level issues are ignored

        return ValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    except (ValueError, TypeError, IndexError):
        pass

    # Fallback: parse line-based output from stderr/stdout
    combined = (stdout + "\n" + stderr).strip()
    if not combined:
        if returncode != 0:
            return ValidationResponse(
                valid=False,
                errors=[
                    ValidationIssue(
                        severity="error",
                        path="(root)",
                        message=f"Validator exited with code {returncode} but produced no output",
                    )
                ],
                warnings=[],
            )
        return ValidationResponse(valid=True, errors=[], warnings=[])

    for line in combined.splitlines():
        line = line.strip()
        if not line:
            continue

        severity = "information"
        if line.startswith("Error") or "ERROR" in line.upper():
            severity = "error"
        elif line.startswith("Warning") or "WARNING" in line.upper():
            severity = "warning"
        else:
            continue

        item = ValidationIssue(
            severity=severity, path="(root)", message=line
        )
        if severity == "error":
            errors.append(item)
        elif severity == "warning":
            warnings.append(item)

    return ValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
