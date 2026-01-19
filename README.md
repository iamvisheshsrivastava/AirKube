# 🚨 <span style="color:red">IN PROGRESS</span> 🚨

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

## Future Extensions & Roadmap
The vision for AirKube includes evolving into a comprehensive **Agentic AI Platform**:

1.  **LangGraph Integration**: Incorporating LangGraph to build stateful multi-agent workflows.
2.  **Agentic Orchestration**: Replacing static rules with an intelligent `Plan-Act-Observe-Reflect` agent loop.
3.  **Real ML Models**: Replacing simulations with actual PyTorch/TensorFlow training jobs.
4.  **RAG Capability**: Adding Retrieval-Augmented Generation for smarter context-aware agents.
5.  **Advanced Monitoring**: Full integration with a Grafana dashboard consuming the Prometheus metrics.
