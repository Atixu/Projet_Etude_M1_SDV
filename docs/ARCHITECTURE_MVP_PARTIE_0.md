# Architecture MVP - Partie 0

## Objectif
Mettre en place un socle technique reproductible pour le MVP de detection de fake news sur Bluesky.

## Perimetre MVP (V1)
- Langues: FR et EN.
- Source: API Bluesky (flux auteur pour demarrage).
- Stockage: MongoDB pour brut et donnees nettoyees.
- Traitements: scripts Python + orchestration Airflow.
- Restitution: dashboard (phase ulterieure) base sur donnees agregees.

## Architecture logique
1. Ingestion
- Script collecte Bluesky.
- Authentification via variables d'environnement.
- Pagination + retry HTTP.

2. Stockage brut
- Collection MongoDB posts_raw.
- Dedupe avec index unique sur post.uri.
- Journalisation de la date de collecte.

3. Nettoyage NLP
- Normalisation de texte.
- Suppression elements non pertinents (URL, mentions, hashtags).
- Ecriture vers posts_clean.

4. Scoring (phases suivantes)
- Classification fake news.
- Analyse emotionnelle.
- Score de credibilite consolide.

5. Orchestration
- Airflow declenche les scripts (collecte, nettoyage, scoring).
- Logs centralises via Airflow + Python logging.

## Choix d'implementation
- Python 3.11+
- requests, python-dotenv, pymongo
- Airflow pour ordonnancement
- Kedro present dans le repo et mobilisable a partir de la phase de structuration pipeline complete

## Contraintes et regles
- Aucun secret dans le code source.
- Configuration via .env local (non committe) et .env.example versionne.
- Reexecution idempotente autant que possible (upsert + cle unique).
- Scripts executables localement avant integration Airflow.

## KPIs MVP
- F1-score fake news (phase modelisation).
- Taux de faux positifs / faux negatifs.
- Temps moyen d'analyse par lot.
- Consommation energetique par run (phase Green IT).

## Definition of Done - Partie 0
- Un nouveau membre peut lancer la collecte en local avec README + .env.example.
- Aucun credential en dur dans le code.
- Les artefacts de cadrage existent (architecture + backlog).
