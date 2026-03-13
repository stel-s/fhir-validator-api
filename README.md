# fhir-validator-api

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[![FHIR R4](https://img.shields.io/badge/FHIR-R4-orange.svg)](https://hl7.org/fhir/R4/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://hub.docker.com/)
[![HAPI FHIR](https://img.shields.io/badge/Powered%20by-HAPI%20FHIR-green.svg)](https://hapifhir.io/)

**A dead-simple REST API for validating FHIR R4 resources — no JVM setup, no config files, just POST and get structured errors back.**

Built for developers who need to validate FHIR output during development and CI/CD pipelines, without the overhead of running a full HAPI FHIR server or wrestling with Java tooling.

🌐 **Live instance:** `https://genomics.ironlabs.gr/fhir/`

---

## Why This Exists

The [HAPI FHIR validator](https://hapifhir.io/hapi-fhir/docs/tools/validation_support_modules.html) is the gold standard for FHIR validation — but it's a Java library. If you're building a Python or Node.js service that produces FHIR resources, integrating it into your workflow means:

- Setting up a JVM
- Managing terminology package downloads (gigabytes of LOINC, SNOMED, ICD-10)
- Parsing cryptic Java output
- Keeping up with FHIR IG releases

This project wraps the HAPI validator CLI in a clean FastAPI service, bundles everything in Docker, and returns structured JSON errors you can actually use.

```json
{
  "valid": false,
  "errors": [
    {
      "severity": "error",
      "path": "Patient.gender",
      "message": "The value 'xyz' is not in the value set 'AdministrativeGender'"
    }
  ],
  "warnings": []
}
```

---

## Features

- ✅ Validates FHIR R4 resources and Bundles (JSON and XML)
- ✅ Supports validation against custom StructureDefinition profiles
- ✅ Returns clean, structured errors — not raw Java stack traces
- ✅ API key authentication
- ✅ Fully Dockerized — single `docker compose up` to run
- ✅ Health endpoint for monitoring
- ✅ Designed for dev/test workflows and CI/CD pipelines

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/stel-s/fhir-validator-api.git
cd fhir-validator-api

# 2. Configure
cp .env.example .env
# Set a strong API_KEY in .env

# 3. Run
docker compose up --build -d

# 4. Validate
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "name": [{ "family": "Smith", "given": ["John"] }],
      "gender": "male",
      "birthDate": "1990-01-15"
    }
  }'
```

> ⚠️ **First request is slow** (30–90s). The JVM starts cold and downloads FHIR packages on first use. Subsequent requests are faster (5–15s).

---

## API Reference

### `GET /health`

Returns the API and validator status. No authentication required.

```json
{
  "status": "ok",
  "validator_jar_found": true,
  "fhir_version": "4.0.1"
}
```

---

### `POST /validate`

Validates a FHIR resource or Bundle.

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | ✅ | Your API key |
| `Content-Type` | ✅ | `application/json`, `application/fhir+json`, or `application/fhir+xml` |

**Request body (JSON)**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `resource` | object | ✅ | The FHIR resource or Bundle |
| `profile` | string | ❌ | StructureDefinition URL to validate against |
| `fhir_version` | string | ❌ | FHIR version override (default: `4.0.1`) |

**Response**

| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | `true` if no errors found |
| `errors` | array | Error-level issues |
| `warnings` | array | Warning-level issues |

Each issue has `severity`, `path`, and `message`.

---

## Examples

### Validate a Patient (JSON)

```bash
curl -X POST https://genomics.ironlabs.gr/fhir/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "id": "example",
      "name": [{ "use": "official", "family": "Smith", "given": ["John"] }],
      "gender": "male",
      "birthDate": "1990-01-15"
    }
  }'
```

### Validate against a profile (US Core Patient)

```bash
curl -X POST https://genomics.ironlabs.gr/fhir/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "name": [{ "family": "Smith" }],
      "gender": "male"
    },
    "profile": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"
  }'
```

### Validate an XML resource

```bash
curl -X POST https://genomics.ironlabs.gr/fhir/validate \
  -H "Content-Type: application/fhir+xml" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '<Patient xmlns="http://hl7.org/fhir">
    <name>
      <use value="official"/>
      <family value="Smith"/>
      <given value="John"/>
    </name>
    <gender value="male"/>
    <birthDate value="1990-01-15"/>
  </Patient>'
```

### Validate an XML file from disk

```bash
curl -X POST https://genomics.ironlabs.gr/fhir/validate \
  -H "Content-Type: application/fhir+xml" \
  -H "X-API-Key: YOUR_API_KEY" \
  --data-binary @path/to/patient.xml
```

### Use in a CI/CD pipeline (GitHub Actions example)

```yaml
- name: Validate FHIR output
  run: |
    RESULT=$(curl -s -X POST $FHIR_VALIDATOR_URL/validate \
      -H "Content-Type: application/json" \
      -H "X-API-Key: $FHIR_API_KEY" \
      -d @tests/fixtures/patient.json)
    
    echo $RESULT | jq .
    
    if [ "$(echo $RESULT | jq .valid)" != "true" ]; then
      echo "FHIR validation failed"
      exit 1
    fi
```

---

## Configuration

All config is via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8080` | Host port |
| `MAX_REQUEST_SIZE_MB` | `10` | Max request body size |
| `API_KEY` | `changeme` | Auth key — **change this** |
| `VALIDATOR_JAR_PATH` | `/app/validator/validator_cli.jar` | Path to HAPI JAR inside container |
| `FHIR_VERSION` | `4.0.1` | Default FHIR version |
| `VALIDATOR_TIMEOUT_SECONDS` | `120` | Max time per validation |

---

## Running Behind a Reverse Proxy

For production, run behind nginx with HTTPS:

```nginx
location /fhir/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
    client_max_body_size 10m;
}
```

---

## Local Development (without Docker)

Requires Java 17+ and Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Download the HAPI validator JAR
mkdir -p validator
curl -L -o validator/validator_cli.jar \
  "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/6.4.0/validator_cli.jar"

# Set VALIDATOR_JAR_PATH=validator/validator_cli.jar in .env

uvicorn app.main:app --reload --port 8080
```

---

## Roadmap

- [ ] Persistent HAPI validator server mode (eliminates JVM cold start per request)
- [ ] Batch validation endpoint (`POST /validate/batch`)
- [ ] Support for FHIR R5
- [ ] Pre-loaded common IGs (US Core, Genomics Reporting, IPS)
- [ ] Async validation with job polling for large Bundles
- [ ] Usage metrics endpoint

---

## Important: PHI and Data Privacy

This API is designed for **development and testing workflows using synthetic or anonymized FHIR data**.

Do not send real Protected Health Information (PHI) to any hosted instance. If you need to validate real patient data, self-host this service within your own compliant infrastructure using the Docker image.

---

## Contributing

Contributions are welcome. To get started:

```bash
git clone https://github.com/stel-s/fhir-validator-api.git
cd fhir-validator-api
# Create a branch, make your changes, open a PR
```

Please open an issue first for significant changes.

---

## License
GNU Affero General Public License v3.0 — see [LICENSE.md](LICENSE.md).

This means you're free to use, modify, and self-host this project. If you distribute a modified version **or run it as a hosted service**, you must open source your modifications under AGPL-3.0. This closes the SaaS loophole present in standard GPL-3.