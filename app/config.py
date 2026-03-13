from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_port: int = 8080
    max_request_size_mb: int = 10
    api_key: str = "changeme-your-secret-api-key"
    validator_jar_path: str = "/app/validator/validator_cli.jar"
    fhir_version: str = "4.0.1"
    validator_timeout_seconds: int = 120

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
