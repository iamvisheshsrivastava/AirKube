

# AirKube  

**Airflow Orchestration + Kubernetes Scalability for Data Pipelines**

## Project Overview
AirKube is a modular data engineering platform designed to demonstrate ingestion, transformation, orchestration, and monitoring workflows. It combines **Apache Airflow** for workflow scheduling, **BigQuery** and **GCS** for warehouse storage, **dbt** for transformation modeling, **FastAPI** for service endpoints, and **Docker/Kubernetes** assets for deployment.

Currently, the project features a functional **pipeline layer** that simulates critical lifecycle stages, a production-ready **Inference API** with built-in observability, and a **news ETL/ELT pipeline** that lands raw data in GCS/BigQuery and materializes reporting tables.

## Key Features

### 1. Orchestration Layer (Airflow)
A set of Airflow DAGs that manage ingestion and downstream handoff:
- **Incremental ingestion** for public news data.
- **Raw and processed warehouse loading** into BigQuery.
- **Conditional branching** based on article availability and pipeline state.
- **Pipeline audit logging** for run tracking and failure analysis.

### 2. Observable Inference Service (FastAPI)
A lightweight, production-grade API framework for model serving (`ml/inference.py`):
- **Endpoints**:
  - `POST /predict`: Single item inference.
  - `POST /batch-predict`: High-throughput batch processing.
  - `GET /health`: Liveness/Readiness probes for K8s.
  - `GET /metrics`: **Prometheus** metrics endpoint.
- **Observability**: Custom middleware tracks request counts, latency, and error rates.
- **Validation**: Pydantic schemas ensure data integrity.

### 3. News Data Pipeline (Airflow + GCP)
A new Airflow DAG (`news_data_pipeline`) that implements a real ETL/ELT flow for public news data:
- **Incremental Extraction**: Fetches only new NewsAPI articles based on the last successful watermark.
- **Python Transformations**: Cleans nulls, normalizes timestamps, and removes duplicates before landing raw data.
- **GCS Landing Zone**: Writes raw JSONL batches to Google Cloud Storage when a bucket is configured; otherwise it loads directly into BigQuery.
- **BigQuery Raw + Processed Tables**: Loads raw data into BigQuery and materializes processed tables with SQL.
- **ELT SQL**: Builds a sentiment-ready dataset and daily article counts inside BigQuery.
- **Audit logging**: Emits structured run events for ingestion, transformation, and loading stages.

### 4. Warehouse Modeling (dbt)
A dbt project under `dbt/` that models the BigQuery warehouse:
- **Source definitions** for raw news tables.
- **Staging models** for cleaned, typed, analytics-ready records.
- **Mart models** for daily article counts and reporting.
- **dbt tests** for uniqueness and not-null validation.

### 5. Observability Stack
- **Prometheus** scrapes the FastAPI service metrics endpoint.
- **Grafana** provides a starter dashboard for request rate, latency, uptime, and error trends.
- **Audit logs** are written locally for pipeline runs and can be forwarded into centralized logging later.

## Project Structure
- `dags/`: Airflow DAG definitions (e.g., `ml_pipeline.py`).
- `ml/`: Source code for the ML logic and FastAPI service.
  - `inference.py`: Main API application.
  - `model.py`: (Simulated) Model logic.
  - `news_pipeline.py`: News extraction, transformation, and load helpers.
  - `news_schemas.py`: Structured models for news raw and processed data.
  - `news_integration.py`: Bridge helpers for ML pipeline handoff.
- `docker/`: Dockerfiles for containerization.
- `k8s/`: Kubernetes manifest files for deployment.
- `terraform/`: Infrastructure-as-code for GCS, BigQuery, and service accounts.
- `dbt/`: BigQuery staging and marts models.
- `observability/`: Prometheus and Grafana configuration.
- `tests/`: Unit and integration tests.

## Agentic Capabilities (NEW 🚀)

AirKube now includes an autonomous agent powered by **LangGraph** and **Gemini**. The agent acts as a true MLOps copilot.

### Operational UI
The Streamlit dashboard remains available for service checks and exploratory control, but the core portfolio focus is now the data platform itself: ingestion, warehouse modeling, orchestration, and monitoring.

### Running the Platform
1. **Install dependencies**: `pip install -r requirements.txt`
2. **Set your API Key**: `export GEMINI_API_KEY=...` (or set in `.env`)
3. **Configure News Pipeline Secrets**: set `NEWS_API_KEY`, `GCP_PROJECT_ID`, and BigQuery dataset/table variables. `NEWS_GCS_BUCKET` is optional.
4. **Run the Dashboard**: `streamlit run dashboard.py`
5. **(Optional) Run CLI Agent**: `python run_agent.py`
6. **Trigger the News Pipeline**: run the `news_data_pipeline` DAG in Airflow.
7. **Provision infrastructure**: `terraform -chdir=terraform init && terraform -chdir=terraform plan`
8. **Build the warehouse models**: `cd dbt && dbt build`
9. **Start monitoring**: `docker compose up prometheus grafana`

### 🧪 Tests & CI/CD
This project includes a comprehensive test suite and GitHub Actions workflow.
- **Run Tests**: `pytest`
- **CI/CD**: Automatically runs tests and linting on every push to `main`.

## Future Extensions & Roadmap
1.  **Terraform**: ✅ Implemented (`terraform/`).
2.  **dbt Warehouse Models**: ✅ Implemented (`dbt/`).
3.  **Monitoring Stack**: ✅ Implemented (`observability/`, `docker-compose.yaml`).
4.  **Pipeline Audit Logging**: ✅ Implemented (`ml/news_pipeline.py`, `dags/news_data_pipeline.py`).
5.  **News ETL/ELT**: ✅ Implemented (`dags/news_data_pipeline.py`, `ml/news_pipeline.py`).
6.  **Real-Time Streaming Ingestion**: Next good addition if you want a stronger data-engineering portfolio.
7.  **Data Quality Automation**: Expand dbt tests or add Great Expectations if you want more validation depth.
