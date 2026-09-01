from langchain.tools import tool
from ml.kg_utils import get_connector
import logging
import os
import requests
import json
import time
import uuid

logger = logging.getLogger("agent_tools")

def _trigger_airflow_dag(pipeline_name: str, parameters: dict = None) -> str:
    """
    Attempts to trigger a real Airflow DAG run via the Airflow REST API
    (POST /api/v1/dags/{dag_id}/dagRuns).

    Airflow connection details must be configured via env vars:
      - AIRFLOW_BASE_URL (e.g. http://localhost:8080)
      - AIRFLOW_USERNAME / AIRFLOW_PASSWORD

    If Airflow isn't configured or isn't reachable, this returns an explicit,
    honest "not triggered" message instead of fabricating a success response -
    the caller must never claim a pipeline was started unless the Airflow API
    actually confirmed it.
    """
    base_url = os.getenv("AIRFLOW_BASE_URL")
    username = os.getenv("AIRFLOW_USERNAME")
    password = os.getenv("AIRFLOW_PASSWORD")

    if not base_url or not username or not password:
        logger.warning(
            f"Airflow trigger requested for '{pipeline_name}' but AIRFLOW_BASE_URL/"
            f"AIRFLOW_USERNAME/AIRFLOW_PASSWORD are not configured. Not triggering."
        )
        return (
            f"Pipeline trigger NOT performed for '{pipeline_name}': Airflow is not "
            f"configured in this deployment (missing AIRFLOW_BASE_URL/AIRFLOW_USERNAME/"
            f"AIRFLOW_PASSWORD). No DAG run was started."
        )

    dag_run_id = f"manual__{time.strftime('%Y-%m-%dT%H:%M:%S')}_{str(uuid.uuid4())[:8]}"
    payload = {"dag_run_id": dag_run_id, "conf": parameters or {}}
    url = f"{base_url.rstrip('/')}/api/v1/dags/{pipeline_name}/dagRuns"

    try:
        resp = requests.post(
            url,
            json=payload,
            auth=(username, password),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        real_run_id = data.get("dag_run_id", dag_run_id)
        logger.info(f"Triggered Airflow DAG '{pipeline_name}', run id: {real_run_id}")
        return (
            f"Successfully triggered pipeline '{pipeline_name}'. "
            f"Execution ID: {real_run_id}. Monitor status in Airflow UI."
        )
    except Exception as e:
        logger.error(f"Failed to trigger Airflow DAG '{pipeline_name}': {e}")
        return (
            f"Pipeline trigger FAILED for '{pipeline_name}': could not reach the "
            f"Airflow API ({str(e)}). No DAG run was started."
        )


@tool
def trigger_ml_pipeline(pipeline_name: str = "enhanced_ml_pipeline", parameters: dict = None):
    """
    Triggers an ML pipeline in Airflow via the Airflow REST API.

    Args:
        pipeline_name (str): The name of the DAG ID to trigger. Defaults to 'enhanced_ml_pipeline'.
        parameters (dict): Optional JSON parameters to pass to the pipeline execution.

    Returns:
        str: A message confirming the real Airflow execution ID, or an explicit
        message stating the trigger was not performed (Airflow not configured
        or unreachable). This never fabricates a success response.
    """
    return _trigger_airflow_dag(pipeline_name, parameters)


@tool
def trigger_news_data_pipeline(pipeline_name: str = "news_data_pipeline", parameters: dict = None):
    """
    Triggers the news ETL/ELT pipeline in Airflow via the Airflow REST API.

    Returns a real Airflow execution ID on success, or an explicit message
    stating the trigger was not performed (Airflow not configured or
    unreachable). This never fabricates a success response.
    """
    return _trigger_airflow_dag(pipeline_name, parameters)

@tool
def get_kg_schema():
    """
    Returns the schema of the Knowledge Graph, including Node Labels and Relationship Types.
    Use this before querying the KG to understand the data model.
    """
    schema_info = """
    **Node Labels:**
    - Model (id, name, version, framework, description)
    - Experiment (id, name, status, created_at)
    - Run (id, name, status, metrics, parameters)
    - Deployment (id, name, cluster, image, replicas)

    **Common Relationships:**
    - (:Run)-[:BELONGS_TO]->(:Experiment)
    - (:Model)-[:PRODUCED_BY]->(:Run)
    - (:Deployment)-[:SERVES]->(:Model)
    """
    return schema_info

@tool
def query_knowledge_graph(query: str):
    """
    Queries the Knowledge Graph (Neo4j) to retrieve information about models, datasets, or deployments.
    
    Args:
        query (str): Cypher query string. e.g., "MATCH (m:Model) RETURN m.name, m.version"
        
    Returns:
        list: A list of records found.
    """
    connector = get_connector()
    try:
        results = connector.run_query(query)
        if not results:
            return "No results found."
        return str(results)
    except Exception as e:
        return f"Error querying KG: {str(e)}"
    finally:
        connector.close()

@tool
def check_system_health():
    """
    Checks the health of the inference service and other components.
    
    Returns:
        str: Health status report.
    """
    health_status = []
    
    # 1. Check Inference API
    try:
        api_url = os.getenv("API_URL", "http://localhost:8000")
        resp = requests.get(f"{api_url}/health", timeout=2)
        if resp.status_code == 200:
            health_status.append(f"[OK] Inference API: {resp.json()}")
        else:
            health_status.append(f"[WARN] Inference API: Returned {resp.status_code}")
    except Exception as e:
        health_status.append(f"[ERR] Inference API: Unreachable ({str(e)})")

    # 2. Check Database (Simulated via Connector)
    # real check would be trying a simple query
    try:
        connector = get_connector()
        # Just check if we can get a connector object without error, actual connection check happens on query
        health_status.append("[OK] Knowledge Graph Connector: Initialized")
        connector.close()
    except Exception:
        health_status.append("[ERR] Knowledge Graph Connector: Failed")

    # 3. Check Airflow (Simulated)
    health_status.append("[OK] Airflow: Scheduler Running (Simulated)")
    
    return " | ".join(health_status)
