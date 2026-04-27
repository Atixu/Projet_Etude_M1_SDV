from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

with DAG(
    dag_id="collect_bluesky_raw",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "owner": "data-engineering",
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["bluesky", "ingestion", "mvp"],
) as dag:

    run_collection = BashOperator(
        task_id="run_bluesky_collection",
        # DOTENV_PATH ensures getapi.py reads the project .env inside Docker.
        bash_command="export DOTENV_PATH=/opt/project/.env && python /opt/project/src/getapi.py",
        execution_timeout=timedelta(minutes=15),
    )
