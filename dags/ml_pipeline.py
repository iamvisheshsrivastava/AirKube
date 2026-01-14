from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago
from datetime import datetime
import random
import time

# Simulation functions
def validate_data(**context):
    """Simulate data validation step."""
    print("Connecting to data source...")
    time.sleep(1)
    print("Validating schema...")
    # Simulate a random validation failure (rarely)
    if random.random() < 0.05:
         raise ValueError("Data validation failed: Schema mismatch")
    print("Data validation successful.")

def train_model(**context):
    """Simulate model training and metric generation."""
    print("Initializing training job...")
    time.sleep(2)
    
    # Simulate varying model performance
    accuracy = 0.75 + (random.random() * 0.24) # Random accuracy between 0.75 and 0.99
    loss = 1 - accuracy
    
    version = f"v{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"Training complete. Accuracy: {accuracy:.4f}, Loss: {loss:.4f}")
    
    # Push metrics and version to XCom for downstream tasks
    context['ti'].xcom_push(key='model_accuracy', value=accuracy)
    context['ti'].xcom_push(key='model_version', value=version)

def evaluate_model(**context):
    """Decide whether to deploy based on model accuracy."""
    accuracy = context['ti'].xcom_pull(task_ids='train_model', key='model_accuracy')
    threshold = 0.82
    
    print(f"Evaluating model. Accuracy: {accuracy:.4f} (Threshold: {threshold})")
    
    if accuracy >= threshold:
        print("Model passed evaluation.")
        return 'build_docker_image'
    else:
        print("Model failed evaluation.")
        return 'notify_training_failure'

default_args = {
    'owner': 'data_science_team',
    'retries': 1,
    'retry_delay': 30, # seconds
}

with DAG(
    dag_id="enhanced_ml_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    default_args=default_args,
    tags=['ml', 'production', 'v2'],
    doc_md="""
    # Enhanced ML Pipeline
    
    This DAG simulates a production-grade machine learning workflow:
    1. **Validate Data**: Checks data quality.
    2. **Train Model**: Simulates training and generates metrics.
    3. **Evaluate**: Decides whether to deploy based on accuracy threshold.
    4. **Build & Deploy**: If successful, builds a Docker image and updates K8s.
    5. **Notify**: If validation or evaluation fails, sends alerts.
    """
) as dag:

    start = EmptyOperator(task_id='start_pipeline')
    
    # Data Prep Stage
    validate = PythonOperator(
        task_id='validate_incoming_data',
        python_callable=validate_data
    )

    # Modeling Stage
    train = PythonOperator(
        task_id='train_model',
        python_callable=train_model
    )

    evaluate = BranchPythonOperator(
        task_id='evaluate_model',
        python_callable=evaluate_model
    )

    # Deployment Stage
    # Note: In a real scenario, we'd pass the version tag to the docker build command
    build_image = BashOperator(
        task_id="build_docker_image",
        bash_command="echo 'Building Docker image... (Simulated)' && echo 'docker build -t demo-ml:{{ ti.xcom_pull(task_ids='train_model', key='model_version') }} -f docker/Dockerfile .'"
    )

    deploy_k8s = BashOperator(
        task_id="deploy_to_kubernetes",
        bash_command="echo 'Deploying to K8s... (Simulated)' && echo 'kubectl set image deployment/ml-app ml-container=demo-ml:{{ ti.xcom_pull(task_ids='train_model', key='model_version') }}'"
    )

    # Handling Failures
    notify_failure = BashOperator(
        task_id="notify_training_failure",
        bash_command="echo 'ALERT: Model accuracy too low. Deployment aborted.'"
    )
    
    end_success = EmptyOperator(task_id='pipeline_finished_successfully')
    end_failure = EmptyOperator(task_id='pipeline_aborted')

    # Wiring the DAG
    start >> validate >> train >> evaluate
    
    evaluate >> build_image >> deploy_k8s >> end_success
    evaluate >> notify_failure >> end_failure
