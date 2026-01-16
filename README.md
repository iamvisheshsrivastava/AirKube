# 🚨 <span style="color:red">IN PROGRESS</span> 🚨

# AirKube

**Airflow Orchestration + Kubernetes Scalability for ML Pipelines**

## Project Overview
AirKube is a production-grade orchestration platform designed to manage the lifecycle of Machine Learning models. It leverages **Apache Airflow** for workflow scheduling and management, and **Kubernetes** for scalable deployment of model training and inference workloads.

Currently, the project features a robust **ML Pipeline** that simulates the critical stages of an MLOps workflow: Data Validation, Model Training, Evaluation, Containerization, and Deployment continuously.

## Features
- **Automated ML Pipeline**: A fully defined Airflow DAG (`enhanced_ml_pipeline`) that orchestrates the ML lifecycle.
- **Conditional Branching**: Smart decision-making to only deploy models that meet accuracy thresholds.
- **Simulated MLOps Tasks**:
  - **Data Validation**: Checks schema and data integrity.
  - **Training**: Simulates model training with performance metrics logging.
  - **Evaluation**: Compares model accuracy against defined thresholds.
  - **CI/CD**: Simulates Docker image building and Kubernetes rolling updates.
- **FastAPI Inference Service**: A lightweight API framework ready for model serving.

## Project Structure
- `dags/`: Contains Airflow DAG definitions (e.g., `ml_pipeline.py`).
- `ml/`: Source code for the Machine Learning models and inference API.
- `docker/`: Dockerfiles for containerizing the application.
- `k8s/`: Kubernetes manifest files for deployment configuration.

## Future Extensions & Roadmap
The vision for AirKube includes evolving into a comprehensive **Agentic AI Platform**. Planned features include:

1.  **LangGraph Integration**: Incorporating LangGraph to build stateful multi-agent workflows.
2.  **Agentic Orchestration**: Replacing static rules with an intelligent `Plan-Act-Observe-Reflect` agent loop.
3.  **Real ML Models**: Replacing simulations with actual PyTorch/TensorFlow training jobs.
4.  **RAG Capability**: Adding Retrieval-Augmented Generation for smarter context-aware agents.
5.  **Advanced Monitoring**: Integration with Prometheus/Grafana for real-time pipeline metrics.
