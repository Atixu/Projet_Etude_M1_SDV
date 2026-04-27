# Handover Context - Projet Thumalien

Date: 2026-04-27

## 1. Objectif du projet
Detection de fake news sur Bluesky avec pipeline NLP, score de credibilite, analyse emotionnelle, dashboard MVP, et suivi Green IT (a finaliser).

## 2. Architecture actuelle
- Collecte: script Python Bluesky API (searchPosts par mots-cles)
- Stockage: MongoDB
- Traitements: scripts Python (cleaning, baseline, emotions, scoring final)
- Orchestration: Airflow (DAG de collecte)
- Visualisation: Streamlit dashboard

## 3. Etat d'avancement par partie
- Partie 0 (cadrage): terminee
- Partie 1 (collecte): terminee
- Partie 2 (nettoyage NLP): terminee
- Partie 3 (baseline fake news): terminee
- Partie 4 (analyse emotionnelle): terminee
- Partie 5 (score final + explicabilite): terminee
- Partie 6 (dashboard MVP): terminee
- Partie 7 (monitoring energetique): a faire
- Partie 8 (tests finaux/docs demo): a faire

## 4. Fichiers clefs
- Collecte: src/getapi.py
- Nettoyage NLP: src/nlp_cleaning.py, src/run_nlp_cleaning.py
- Baseline fake news: src/run_baseline.py
- Analyse emotionnelle: src/emotion_analysis.py, src/run_emotion_analysis.py
- Score final: src/run_final_scoring.py
- Dashboard: src/dashboard_app.py
- Airflow DAG: airflow/dags/run_pipeline.py
- Setup: README.md, .env.example, requirements.txt

## 5. Schema de donnees Mongo
Base: bluesky

Collections:
- posts_raw: donnees brutes collecte API
- posts_clean: donnees nettoyees + enrichies

Champs importants dans posts_clean:
- text, clean_text, lang, token_count
- credibility_score, prob_fake, prob_real, predicted_label, alert_level
- sentiment_compound, sentiment_label
- emotion_scores, dominant_emotion
- final_credibility_score, final_risk_score, final_alert_level
- score_breakdown, explanation_text

## 6. Resultats observes
### Collecte
- fetched total: 4729
- uniques upserted: 4667

### Nettoyage NLP
- raw: 4667
- clean: 4618
- skipped: 49

### Baseline fake news
- Modele: TF-IDF + LogisticRegression
- Dataset train: GonzaloA/fake_news (HuggingFace)
- F1 weighted test: 0.9767
- Scoring sur posts_clean:
  - fake: 4476
  - real: 142

### Emotions
- positive: 1439
- neutral: 1233
- negative: 1946

### Score final combine
- low: 315
- medium: 3194
- high: 1109
- score moyen: 0.4417

## 7. Decisions techniques importantes
1. Changement de strategie de collecte:
- Abandon de getAuthorFeed (compte auteur vide)
- Utilisation de searchPosts par mots-cles (FR/EN)

2. Normalisation cross-platform:
- Renommage script collecte en src/getapi.py (casse compatible Linux/macOS)

3. Explicabilite:
- Champ explanation_text genere pour chaque post
- score_breakdown conserve les composantes du score final

4. Portabilite repo:
- .gitignore nettoye (env, logs, models)
- .env.example fourni

## 8. Incidents rencontres et resolutions
1. dotenv manquant
- Cause: dependances non installees
- Fix: pip install -r requirements.txt

2. Variables env absentes
- Cause: .env manquant
- Fix: creer .env depuis .env.example

3. BLUESKY actor invalide
- Cause: email au lieu de handle
- Fix: fallback handle session + collecte par keywords

4. Mongo inaccessible
- Cause: service non demarre
- Fix: demarrage Mongo local Docker

5. Warning requests dependency mismatch
- Etat: non bloquant
- Action future: figer versions compatibles pour supprimer warning

6. Warning HuggingFace trust_remote_code
- Etat: dataset charge mais warning
- Action future: retirer argument trust_remote_code dans run_baseline.py

## 9. Comment relancer le projet depuis zero
1. Installer Python 3.11+
2. Installer dependances:
- pip install -r requirements.txt
3. Creer configuration:
- cp .env.example .env (ou Copy-Item sous PowerShell)
4. Remplir .env (Bluesky + Mongo)
5. Lancer pipeline:
- python src/getapi.py
- python src/run_nlp_cleaning.py
- python src/run_baseline.py
- python src/run_emotion_analysis.py
- python src/run_final_scoring.py
6. Lancer dashboard:
- streamlit run src/dashboard_app.py

## 10. Variables d'environnement principales
- BLUESKY_IDENTIFIER
- BLUESKY_APP_PASSWORD
- MONGO_URI
- MONGO_DB
- MONGO_COLLECTION_RAW
- MONGO_COLLECTION_CLEAN

Optionnelles:
- BLUESKY_LIMIT
- BLUESKY_MAX_PAGES
- BLUESKY_SEARCH_TERMS
- DOTENV_PATH

## 11. Ce qu'il reste a faire (priorite)
1. Partie 7: Monitoring energetique
- Integrer CodeCarbon sur run_baseline.py et inference
- Produire rapport consommation comparatif

2. Partie 8: Fiabilisation
- Tests unitaires scripts critiques
- Test integration end-to-end
- Documentation soutenance (slides + scenario demo)

## 12. Push GitHub
- Remote: origin https://github.com/Atixu/Projet_Etude_M1_SDV.git
- Branche de travail: dev
- Commit recent: aa0886f (pipeline + dashboard)

## 13. Notes securite
- Ne jamais versionner .env
- Ne jamais stocker de credentials en clair dans le code
- Utiliser app password Bluesky, pas le mot de passe principal
