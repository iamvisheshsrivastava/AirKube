from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id="simple_ml_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    train = BashOperator(
        task_id="train_model",
        bash_command="echo 'Training model (simulated)'"
    )

    build_image = BashOperator(
        task_id="build_docker_image",
        bash_command="docker build -t demo-ml -f docker/Dockerfile ."
    )

    deploy_k8s = BashOperator(
        task_id="deploy_to_kubernetes",
        bash_command="kubectl apply -f k8s/deployment.yaml"
    )

    train >> build_image >> deploy_k8s
