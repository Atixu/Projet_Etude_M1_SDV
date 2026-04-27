# Partie 1 - Collecte Bluesky et stockage brut

## Objectif
Collecter des posts Bluesky de maniere robuste et les stocker en brut dans MongoDB.

## Fonctionnel implemente
- Authentification Bluesky via `com.atproto.server.createSession`.
- Extraction paginee de feed auteur (`app.bsky.feed.getAuthorFeed`).
- Retries HTTP automatiques sur erreurs transitoires (429/5xx).
- Persistance MongoDB en mode upsert avec deduplication (`post.uri` unique).
- Journalisation des volumes et metadonnees de collecte (`collected_at`).

## Fichiers principaux
- Script de collecte: `src/getapi.py`
- DAG Airflow: `airflow/dags/run_pipeline.py`
- Stack Airflow: `airflow/docker-compose.yaml`
- Variables d'environnement: `.env.example`

## Variables d'environnement requises
- `BLUESKY_IDENTIFIER`
- `BLUESKY_APP_PASSWORD`
- `MONGO_URI`

Variables optionnelles:
- `BLUESKY_ACTOR` (defaut: `BLUESKY_IDENTIFIER`)
- `BLUESKY_BASE_URL` (defaut: `https://bsky.social`)
- `BLUESKY_LIMIT` (defaut: 100)
- `BLUESKY_MAX_PAGES` (defaut: 5)
- `MONGO_DB` (defaut: `bluesky`)
- `MONGO_COLLECTION_RAW` (defaut: `posts_raw`)

## Run local
1. Installer dependances:
```bash
pip install -r requirements.txt
```
2. Initialiser config:
```bash
cp .env.example .env
```
3. Completer `.env` avec vos credentials.
4. Lancer la collecte:
```bash
python src/getapi.py
```

## Run Airflow (Docker)
1. Copier votre `.env` a la racine du projet.
2. Demarrer Airflow:
```bash
cd airflow
docker compose up -d
```
3. Ouvrir Airflow UI: `http://localhost:8080` (airflow/airflow).
4. Declencher le DAG `collect_bluesky_raw`.

## Validation attendue (Definition of Done Partie 1)
- Le script collecte au moins un lot de posts sans erreur bloquante.
- La collection Mongo brute est alimentee.
- Les relances ne dupliquent pas les documents (`post.uri` unique).
- Les logs affichent pages, volumes et stats d'upsert.

## Points de controle en demo
- Montrer les logs de pagination (`Page X fetched...`).
- Montrer index unique Mongo sur `post.uri`.
- Montrer un document brut avec `feed_context.collected_at`.
