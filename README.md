# FHIR Validator API

A REST API for validating FHIR R4 resources using the [HAPI FHIR Validator CLI](https://github.com/hapifhir/org.hl7.fhir.core). Built with FastAPI and Dockerized with Java + the validator JAR bundled in the image.

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env to set your API_KEY and preferred port

# 2. Build and run
docker compose up --build -d

# 3. Check health
curl http://localhost:8080/health
```

## Configuration

All configuration is done via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8080` | Host port the API is exposed on |
| `MAX_REQUEST_SIZE_MB` | `10` | Maximum allowed request body size |
| `API_KEY` | `changeme-your-secret-api-key` | API key for authentication |
| `VALIDATOR_JAR_PATH` | `/app/validator/validator_cli.jar` | Path to the HAPI validator JAR inside the container |
| `FHIR_VERSION` | `4.0.1` | Default FHIR version (R4) |
| `VALIDATOR_TIMEOUT_SECONDS` | `120` | Max time for a single validation call |

## Authentication

All `/validate` requests require an `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" ...
```

The `/health` endpoint does not require authentication.

## API Reference

### GET /health

Returns the API and validator status.

**Response:**
```json
{
  "status": "ok",
  "validator_jar_found": true,
  "fhir_version": "4.0.1"
}
```

### POST /validate

Validates a FHIR resource or bundle.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `resource` | object | Yes | The FHIR resource or Bundle JSON |
| `profile` | string | No | StructureDefinition URL to validate against |
| `fhir_version` | string | No | FHIR version override (default: `4.0.1`) |

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | `true` if no errors were found |
| `errors` | array | List of error-level issues |
| `warnings` | array | List of warning-level issues |

Each issue contains `severity`, `path`, and `message`.

## Examples

### Validate a Patient resource

```bash
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme-your-secret-api-key" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "id": "example-patient",
      "meta": {
        "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]
      },
      "name": [
        {
          "use": "official",
          "family": "Smith",
          "given": ["John", "Michael"]
        }
      ],
      "gender": "male",
      "birthDate": "1990-01-15",
      "telecom": [
        {
          "system": "phone",
          "value": "+1-555-123-4567",
          "use": "home"
        },
        {
          "system": "email",
          "value": "john.smith@example.com"
        }
      ],
      "address": [
        {
          "use": "home",
          "line": ["123 Main St"],
          "city": "Springfield",
          "state": "IL",
          "postalCode": "62704",
          "country": "US"
        }
      ]
    }
  }'
```

### Validate an Observation (vital sign)

```bash
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme-your-secret-api-key" \
  -d '{
    "resource": {
      "resourceType": "Observation",
      "id": "blood-pressure",
      "status": "final",
      "category": [
        {
          "coding": [
            {
              "system": "http://terminology.hl7.org/CodeSystem/observation-category",
              "code": "vital-signs",
              "display": "Vital Signs"
            }
          ]
        }
      ],
      "code": {
        "coding": [
          {
            "system": "http://loinc.org",
            "code": "85354-9",
            "display": "Blood pressure panel"
          }
        ]
      },
      "subject": {
        "reference": "Patient/example-patient"
      },
      "effectiveDateTime": "2024-01-15T10:30:00Z",
      "component": [
        {
          "code": {
            "coding": [
              {
                "system": "http://loinc.org",
                "code": "8480-6",
                "display": "Systolic blood pressure"
              }
            ]
          },
          "valueQuantity": {
            "value": 120,
            "unit": "mmHg",
            "system": "http://unitsofmeasure.org",
            "code": "mm[Hg]"
          }
        },
        {
          "code": {
            "coding": [
              {
                "system": "http://loinc.org",
                "code": "8462-4",
                "display": "Diastolic blood pressure"
              }
            ]
          },
          "valueQuantity": {
            "value": 80,
            "unit": "mmHg",
            "system": "http://unitsofmeasure.org",
            "code": "mm[Hg]"
          }
        }
      ]
    }
  }'
```

### Validate a Bundle (e.g. a document or transaction)

```bash
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme-your-secret-api-key" \
  -d '{
    "resource": {
      "resourceType": "Bundle",
      "type": "transaction",
      "entry": [
        {
          "fullUrl": "urn:uuid:patient-1",
          "resource": {
            "resourceType": "Patient",
            "name": [{"family": "Doe", "given": ["Jane"]}],
            "gender": "female",
            "birthDate": "1985-07-20"
          },
          "request": {
            "method": "POST",
            "url": "Patient"
          }
        },
        {
          "fullUrl": "urn:uuid:condition-1",
          "resource": {
            "resourceType": "Condition",
            "clinicalStatus": {
              "coding": [
                {
                  "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                  "code": "active"
                }
              ]
            },
            "code": {
              "coding": [
                {
                  "system": "http://snomed.info/sct",
                  "code": "44054006",
                  "display": "Type 2 diabetes mellitus"
                }
              ]
            },
            "subject": {
              "reference": "urn:uuid:patient-1"
            }
          },
          "request": {
            "method": "POST",
            "url": "Condition"
          }
        }
      ]
    }
  }'
```

### Validate against a specific profile

```bash
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme-your-secret-api-key" \
  -d '{
    "resource": {
      "resourceType": "Patient",
      "name": [{"family": "Smith"}],
      "gender": "male"
    },
    "profile": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"
  }'
```

### Validate a MedicationRequest

```bash
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme-your-secret-api-key" \
  -d '{
    "resource": {
      "resourceType": "MedicationRequest",
      "status": "active",
      "intent": "order",
      "medicationCodeableConcept": {
        "coding": [
          {
            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
            "code": "1049502",
            "display": "Lisinopril 10 MG Oral Tablet"
          }
        ]
      },
      "subject": {
        "reference": "Patient/example-patient"
      },
      "authoredOn": "2024-01-15",
      "requester": {
        "reference": "Practitioner/example-doctor"
      },
      "dosageInstruction": [
        {
          "text": "Take 1 tablet daily",
          "timing": {
            "repeat": {
              "frequency": 1,
              "period": 1,
              "periodUnit": "d"
            }
          },
          "route": {
            "coding": [
              {
                "system": "http://snomed.info/sct",
                "code": "26643006",
                "display": "Oral route"
              }
            ]
          },
          "doseAndRate": [
            {
              "doseQuantity": {
                "value": 1,
                "unit": "tablet",
                "system": "http://terminology.hl7.org/CodeSystem/v3-orderableDrugForm",
                "code": "TAB"
              }
            }
          ]
        }
      ]
    }
  }'
```

### Example response (with issues)

```json
{
  "valid": false,
  "errors": [
    {
      "severity": "error",
      "path": "Patient.gender",
      "message": "The value provided ('xyz') is not in the value set 'AdministrativeGender'"
    }
  ],
  "warnings": [
    {
      "severity": "warning",
      "path": "Patient",
      "message": "A resource should have narrative for robust management"
    }
  ]
}
```

## Performance Notes

- **First request is slow**: The HAPI validator JVM starts cold and downloads/caches FHIR packages on first use. Expect 30-90 seconds for the first validation.
- **Subsequent requests** are faster but still spawn a new JVM process each time (typically 5-15 seconds).
- For high-throughput use cases, consider running the HAPI validator as a persistent server instead of a CLI subprocess.

## Development

To run locally without Docker (requires Java 17+ and the validator JAR):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Download the validator JAR
mkdir -p validator
curl -L -o validator/validator_cli.jar \
  "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/6.4.0/validator_cli.jar"

# Update .env
# VALIDATOR_JAR_PATH=validator/validator_cli.jar

uvicorn app.main:app --reload --port 8080
```
