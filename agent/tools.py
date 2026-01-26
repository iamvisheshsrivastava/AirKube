from langchain.tools import tool
from ml.kg_utils import get_connector
import logging

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
    # Simulated check
    return "System Status: [OK] Inference API (Active), [OK] Database (Connected), [OK] Airflow (Scheduler Running)"
