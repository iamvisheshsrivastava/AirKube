from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago
from datetime import datetime
import random
import time
import mlflow
import os

# Define MLflow Experiment
MLFLOW_EXPERIMENT = "AirKube_Experiment"
mlflow.set_experiment(MLFLOW_EXPERIMENT)

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
    """Simulate model training and metric generation with MLflow logging."""
    print("Initializing training job...")
    
    with mlflow.start_run() as run:
        # Simulate training parameters
        params = {
            "epochs": 10,
            "learning_rate": 0.01,
            "batch_size": 32
        }
        mlflow.log_params(params)
        
        time.sleep(2)
        
        # Simulate varying model performance
        accuracy = 0.75 + (random.random() * 0.24) # Random accuracy between 0.75 and 0.99
        loss = 1 - accuracy
        
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("loss", loss)
        
        # Generate a fake model artifact
        os.makedirs("model_output", exist_ok=True)
        with open("model_output/model.pkl", "w") as f:
            f.write(f"Model accuracy: {accuracy}")
        
        mlflow.log_artifact("model_output/model.pkl", artifact_path="model")
        
        run_id = run.info.run_id
        print(f"Training complete. Accuracy: {accuracy:.4f}, Run ID: {run_id}")
        
        # Push metrics involved in decision making to XCom
        context['ti'].xcom_push(key='model_accuracy', value=accuracy)
        context['ti'].xcom_push(key='mlflow_run_id', value=run_id)

def evaluate_model(**context):
    """Decide whether to proceed to registry based on model accuracy."""
    accuracy = context['ti'].xcom_pull(task_ids='train_model', key='model_accuracy')
    threshold = 0.82
    
    print(f"Evaluating model. Accuracy: {accuracy:.4f} (Threshold: {threshold})")
    
    if accuracy >= threshold:
        print("Model passed evaluation.")
        return 'register_model'
    else:
        print("Model failed evaluation.")
        return 'notify_training_failure'

def register_model(**context):
    """Register the model in MLflow Model Registry."""
    run_id = context['ti'].xcom_pull(task_ids='train_model', key='mlflow_run_id')
    model_name = "AirKube_Model"
    
    print(f"Registering model from Run ID: {run_id} as '{model_name}'")
    
    # In a real scenario, we would use mlflow.register_model()
    # model_uri = f"runs:/{run_id}/model"
    # mv = mlflow.register_model(model_uri, model_name)
    # version = mv.version
    
    # Simulating versioning for this exercise
    version = f"v{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"Model registered. Version: {version}")
    
    context['ti'].xcom_push(key='model_version', value=version)

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
    tags=['ml', 'production', 'v2', 'mlflow'],
    doc_md="""
    # Enhanced ML Pipeline with MLflow
    
    This DAG manages the end-to-end ML lifecycle:
    1. **Pre-processing**: Validates input data.
    2. **Training**: Trains model and logs to MLflow.
    3. **Evaluation**: Checks metrics against threshold.
    4. **Registry**: Registers the model if compatible.
    5. **Delivery**: Builds Docker image with model version.
    6. **Deployment**: Updates Kubernetes deployment.
    """
) as dag:

    start = EmptyOperator(task_id='start_pipeline')
    
    # 1. Pre-processing
    validate = PythonOperator(
        task_id='validate_incoming_data',
        python_callable=validate_data
    )

    # 2. Training
    train = PythonOperator(
        task_id='train_model',
        python_callable=train_model
    )

    # 3. Evaluation
    evaluate = BranchPythonOperator(
        task_id='evaluate_model',
        python_callable=evaluate_model
    )

    # 4. Model Registry
    register = PythonOperator(
        task_id='register_model',
        python_callable=register_model
    )

    # 5. Delivery
    build_image = BashOperator(
        task_id="build_docker_image",
        bash_command="echo 'Building Docker image... (Simulated)' && echo 'docker build -t demo-ml:{{ ti.xcom_pull(task_ids='register_model', key='model_version') }} -f docker/Dockerfile .'"
    )

    # 6. Deployment
    deploy_k8s = BashOperator(
        task_id="deploy_to_kubernetes",
        bash_command="echo 'Deploying to K8s... (Simulated)' && echo 'kubectl set image deployment/ml-app ml-api=demo-ml:{{ ti.xcom_pull(task_ids='register_model', key='model_version') }}'"
    )

    # Handling Failures
    notify_failure = BashOperator(
        task_id="notify_training_failure",
        bash_command="echo 'ALERT: Model accuracy too low. Pipeline aborted.'"
    )
    
    end_success = EmptyOperator(task_id='pipeline_finished_successfully')
    end_failure = EmptyOperator(task_id='pipeline_aborted')

    # Wiring the DAG
    start >> validate >> train >> evaluate
    
    evaluate >> register >> build_image >> deploy_k8s >> end_success
    evaluate >> notify_failure >> end_failure
