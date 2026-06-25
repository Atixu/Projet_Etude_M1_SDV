"""DAG Airflow — Pipeline complet Bluesky fake-news.

Orchestration quotidienne :
  1. collect_bluesky  : collecte les posts via l'API Bluesky (getapi.py)
  2. nlp_cleaning     : pipeline Kedro (clean / detect_lang / normalize /
                        tokenize / lemmatize / load → MongoDB posts_clean_kedro)

Lancement manuel :
    airflow dags trigger bluesky_pipeline
"""

import os
from datetime import datetime, timedelta

from airflow.sdk import dag
from airflow.providers.standard.operators.bash import BashOperator

PROJECT_ROOT = os.path.join(
    os.path.expanduser("~"),
    "Documents", "M1-BigDATA&IA", "00-Projet", "Projet_Etude_M1_SDV",
)
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python")
KEDRO_BIN = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "kedro")
ETL_DIR = os.path.join(PROJECT_ROOT, "etl-bluesky")
SRC_DIR = os.path.join(PROJECT_ROOT, "src")


DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


@dag(
    dag_id="bluesky_pipeline",
    description="Collecte Bluesky + NLP Kedro — pipeline complet fake-news",
    start_date=datetime(2025, 1, 1),
    schedule="0 0 * * *",  # chaque jour a minuit
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["bluesky", "nlp", "kedro", "fake-news"],
)
def bluesky_pipeline():

    # -------------------------------------------------------------------------
    # Tache 1 : Collecte des posts Bluesky
    # Appelle getapi.py qui interroge l'API Bluesky et insere dans posts_raw
    # -------------------------------------------------------------------------
    collect = BashOperator(
        task_id="collect_bluesky",
        bash_command=(
            f'"{VENV_PYTHON}" "{SRC_DIR}/getapi.py"'
        ),
        execution_timeout=timedelta(minutes=30),
        doc_md="Collecte les posts Bluesky via l'API et les insere dans MongoDB `posts_raw`.",
    )

    # -------------------------------------------------------------------------
    # Tache 2 : Pipeline NLP Kedro
    # 7 nodes : extract -> clean -> detect_lang -> normalize ->
    #           tokenize -> lemmatize -> load (posts_clean_kedro)
    # -------------------------------------------------------------------------
    nlp = BashOperator(
        task_id="nlp_cleaning",
        bash_command=(
            f'cd "{ETL_DIR}" && '
            f'PYTHONUTF8=1 "{KEDRO_BIN}" run --pipeline nlp_cleaning'
        ),
        execution_timeout=timedelta(minutes=30),
        doc_md=(
            "Pipeline Kedro NLP : nettoyage, detection langue, normalisation, "
            "tokenisation, lemmatisation et chargement dans `posts_clean_kedro`."
        ),
    )

    # Dependance : la collecte doit reussir avant le nettoyage NLP
    collect >> nlp


bluesky_pipeline()
