from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago
from datetime import datetime
import mlflow
import logging

from ml.kg_extraction import extract_entities_from_text
from ml.kg_validation import validate_extraction
from ml.kg_ingestion import ingest_graph

logger = logging.getLogger("airflow.task")

# MLflow Setup
mlflow.set_experiment("AirKube_KG_Pipeline")

def extract_knowledge(**context):
    """
    Simulates fetching a document and running LLM extraction.
    """
    logger.info("Fetching unstructured MLOps text...")
    sample_text = """
    We have successfully trained ResNet50 v2 using PyTorch. The experiment 'Vision Upgrade 2024' is active.
    Run #101 completed with 92% accuracy and 0.21 loss.
    The model is currently deployed to the US-East K8s cluster as 'dep_prod_vision' with 3 replicas.
    """
    
    with mlflow.start_run(run_name="KG_Extraction"):
        extraction = extract_entities_from_text(sample_text)
        
        # Log basic stats
        mlflow.log_metric("entities_extracted", len(extraction.models) + len(extraction.runs) + len(extraction.deployments))
        
        # Pass data to XCom (serializing Pydantic to JSON dicts)
        context['ti'].xcom_push(key='extraction_result', value=extraction.dict())

def validate_knowledge(**context):
    """
    Runs the Validation Agent loop.
    """
    data = context['ti'].xcom_pull(task_ids='extract_knowledge', key='extraction_result')
    
    # Reconstruct object (simplified)
    # In prod, we'd use the Pydantic parse, here we pass dict to a wrapper if needed
    # but our mock validator in this file assumes object. 
    # Let's blindly cast for the simulation or import the class.
    from ml.kg_schemas import ExtractionResult
    extraction = ExtractionResult(**data)
    
    result = validate_extraction(extraction)
    
    if result.is_valid:
        return 'ingest_to_neo4j'
    else:
        logger.error(f"Validation failed: {result.reasoning}")
        mlflow.log_param("validation_status", "FAILED")
        mlflow.log_text(result.reasoning, "validation_failure.txt")
        return 'flag_for_human_review'

def ingest_knowledge(**context):
    """
    Ingests validated data into Neo4j.
    """
    data = context['ti'].xcom_pull(task_ids='extract_knowledge', key='extraction_result')
    from ml.kg_schemas import ExtractionResult
    extraction = ExtractionResult(**data)
    
    ingest_graph(extraction, model_version="gpt-4-turbo-sim")
    mlflow.log_param("ingestion_status", "SUCCESS")

default_args = {
    'owner': 'knowledge_engineer',
    'retries': 0,
}

with DAG(
    dag_id="mlops_kg_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    default_args=default_args,
    tags=['kg', 'neo4j', 'llm', 'mlops']
) as dag:

    start = EmptyOperator(task_id='start_extraction')

    extract = PythonOperator(
        task_id='extract_knowledge',
        python_callable=extract_knowledge
    )

    validate = BranchPythonOperator(
        task_id='validate_knowledge',
        python_callable=validate_knowledge
    )

    ingest = PythonOperator(
        task_id='ingest_to_neo4j',
        python_callable=ingest_knowledge
    )

    flag_review = EmptyOperator(task_id='flag_for_human_review')
    end = EmptyOperator(task_id='pipeline_complete')

    start >> extract >> validate
    validate >> ingest >> end
    validate >> flag_review
