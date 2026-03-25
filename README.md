

# AirKube

**Airflow Orchestration + Kubernetes Scalability for ML Pipelines**

## Project Overview
AirKube is a modular MLOps platform designed to demonstrate the lifecycle of Machine Learning models. It combines **Apache Airflow** for workflow scheduling, **FastAPI** for model serving, and **MLflow** for experiment tracking, with **Kubernetes** manifests ready for scalable deployment.

Currently, the project features a functional **ML Pipeline** that simulates critical MLOps stages—from Data Validation to Deployment—and a production-ready **Inference API** with built-in observability.

It also now includes a production-style **News ETL/ELT pipeline** that ingests public news data into **GCS** and **BigQuery** for downstream analytics and ML consumption.

## Key Features

### 1. Enhanced ML Pipeline (Airflow)
A comprehensive Airflow DAG (`enhanced_ml_pipeline`) that manages the ML lifecycle:
- **MLflow Integration**: automatically logs training parameters, metrics (accuracy, loss), and artifacts.
- **Conditional Branching**: Implements "Gatekeeper" logic to only deploy models that meet strict accuracy thresholds.
- **Simulated Stages**:
  - **Data Validation**: Randomly simulates schema checks and failures.
  - **Training**: Simulates model training time and variable performance.
  - **Model Registry**: Simulates versioning and artifact storage.
  - **CI/CD**: Simulates Docker image builds and Kubernetes rolling updates.

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
- **GCS Landing Zone**: Writes raw JSONL batches to Google Cloud Storage.
- **BigQuery Raw + Processed Tables**: Loads raw data into BigQuery and materializes processed tables with SQL.
- **ELT SQL**: Builds a sentiment-ready dataset and daily article counts inside BigQuery.
- **ML Integration**: Passes the processed BigQuery table reference into `enhanced_ml_pipeline` for downstream use.

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
- `tests/`: Unit and integration tests.

## Agentic Capabilities (NEW 🚀)

AirKube now includes an autonomous agent powered by **LangGraph** and **OpenAI**. The agent acts as a true MLOps copilot.

### 🌟 New: Interactive Dashboard
We have introduced a **Streamlit Dashboard** for a rich visual experience.
- **Chat Interface**: Talk to the MLOps agent directly.
- **Extraction Playground**: Test the new LLM-based Knowledge Extraction on your own text.
- **Graph Explorer**: Query and visualize the Knowledge Graph.

### Capabilities:
- **Real-Time Knowledge Extraction**: Uses **GPT-4** to parse unstructured text into structured KG entities (Models, Runs, metrics).
- **Smart Schema Awareness**: Automatically inspects the KG schema before querying using `get_kg_schema`.
- **Pipeline Orchestration**: Trigger Airflow DAGs from natural language.
- **System Observability**: Check the health of Inference APIs and other components.

### Running the Platform
1. **Install dependencies**: `pip install -r requirements.txt`
2. **Set your API Key**: `export OPENAI_API_KEY=sk-...` (or set in `.env`)
3. **Configure News Pipeline Secrets**: set `NEWS_API_KEY`, `GCP_PROJECT_ID`, `NEWS_GCS_BUCKET`, and BigQuery dataset/table variables.
4. **Run the Dashboard**: `streamlit run dashboard.py`
5. **(Optional) Run CLI Agent**: `python run_agent.py`
6. **Trigger the News Pipeline**: run the `news_data_pipeline` DAG in Airflow.

### 🧪 Tests & CI/CD
This project includes a comprehensive test suite and GitHub Actions workflow.
- **Run Tests**: `pytest`
- **CI/CD**: Automatically runs tests and linting on every push to `main`.

## Future Extensions & Roadmap
1.  **LangGraph Integration**: ✅ Implemented.
2.  **Agentic Orchestration**: ✅ Implemented (`agent/graph.py`).
3.  **Real Knowledge Extraction**: ✅ Implemented (`ml/kg_extraction.py` with GPT-4).
4.  **Interactive UI**: ✅ Implemented (`dashboard.py`).
5.  **News ETL/ELT**: ✅ Implemented (`dags/news_data_pipeline.py`, `ml/news_pipeline.py`).
6.  **Real ML Models**: Replacing simulations with actual PyTorch/TensorFlow training jobs.
7.  **RAG Capability**: Deepening the KG integration for smarter context.
8.  **Advanced Monitoring**: Full integration with a Grafana dashboard consuming the Prometheus metrics.
