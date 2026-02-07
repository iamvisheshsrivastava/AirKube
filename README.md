

# AirKube

**Airflow Orchestration + Kubernetes Scalability for ML Pipelines**

## Project Overview
AirKube is a modular MLOps platform designed to demonstrate the lifecycle of Machine Learning models. It combines **Apache Airflow** for workflow scheduling, **FastAPI** for model serving, and **MLflow** for experiment tracking, with **Kubernetes** manifests ready for scalable deployment.

Currently, the project features a functional **ML Pipeline** that simulates critical MLOps stages—from Data Validation to Deployment—and a production-ready **Inference API** with built-in observability.

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

## Project Structure
- `dags/`: Airflow DAG definitions (e.g., `ml_pipeline.py`).
- `ml/`: Source code for the ML logic and FastAPI service.
  - `inference.py`: Main API application.
  - `model.py`: (Simulated) Model logic.
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
3. **Run the Dashboard**: `streamlit run dashboard.py`
4. **(Optional) Run CLI Agent**: `python run_agent.py`

## Future Extensions & Roadmap
1.  **LangGraph Integration**: ✅ Implemented.
2.  **Agentic Orchestration**: ✅ Implemented (`agent/graph.py`).
3.  **Real Knowledge Extraction**: ✅ Implemented (`ml/kg_extraction.py` with GPT-4).
4.  **Interactive UI**: ✅ Implemented (`dashboard.py`).
5.  **Real ML Models**: Replacing simulations with actual PyTorch/TensorFlow training jobs.
6.  **RAG Capability**: Deepening the KG integration for smarter context.
7.  **Advanced Monitoring**: Full integration with a Grafana dashboard consuming the Prometheus metrics.
