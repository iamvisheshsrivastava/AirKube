from langchain.tools import tool
from ml.kg_utils import get_connector
import logging
import requests
import json

logger = logging.getLogger("agent_tools")

@tool
def trigger_ml_pipeline(pipeline_name: str = "enhanced_ml_pipeline", parameters: dict = None):
    """
    Triggers an ML pipeline in Airflow.
    
    Args:
        pipeline_name (str): The name of the DAG ID to trigger. Defaults to 'enhanced_ml_pipeline'.
        parameters (dict): Optional JSON parameters to pass to the pipeline execution.
        
    Returns:
        str: execution_id of the triggered pipeline.
    """
    # In a real scenario, this would use the Airflow REST API.
    # For this demo, we simulate the request.
    import time
    import uuid
    
    exec_id = f"manual__{time.strftime('%Y-%m-%dT%H:%M:%S')}_{str(uuid.uuid4())[:8]}"
    logger.info(f"Triggering Airflow DAG '{pipeline_name}' with params: {parameters}")
    
    return f"Successfully triggered pipeline '{pipeline_name}'. Execution ID: {exec_id}. Monitor status in Airflow UI."

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
        resp = requests.get("http://localhost:8000/health", timeout=2)
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
