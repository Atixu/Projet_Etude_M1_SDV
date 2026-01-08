from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id="run_external_python_script",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # manuel
    catchup=False,
) as dag:

    run_script = BashOperator(
        task_id="run_pipeline",
        bash_command="python /opt/project/src/getAPI.py",
    )
