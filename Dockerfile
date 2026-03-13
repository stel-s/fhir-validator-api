FROM eclipse-temurin:17-jre-jammy AS java-base

FROM python:3.12-slim

# Install Java runtime from temurin image
COPY --from=java-base /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="${JAVA_HOME}/bin:${PATH}"

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the HAPI FHIR validator CLI JAR
ARG VALIDATOR_VERSION=6.4.0
RUN mkdir -p /app/validator && \
    apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -L -o /app/validator/validator_cli.jar \
    "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/${VALIDATOR_VERSION}/validator_cli.jar" && \
    apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app/ /app/app/
COPY .env.example /app/.env

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
