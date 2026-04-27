# Projet_Etude_M1_SDV

Projet d'etude SDV 2025 M1.

## Prerequis

- Python 3.11+
- MongoDB local ou distant

## Installation

1. Installer les dependances:

```bash
pip install -r requirements.txt
```

2. Creer la configuration locale:

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

3. Renseigner les variables dans `.env`.

## Execution du pipeline (ordre recommande)

1. Collecte Bluesky -> Mongo brut:

```bash
python src/getapi.py
```

2. Nettoyage NLP -> Mongo clean:

```bash
python src/run_nlp_cleaning.py
```

3. Baseline fake news (entrainement + scoring):

```bash
python src/run_baseline.py
```

4. Analyse emotionnelle:

```bash
python src/run_emotion_analysis.py
```

5. Score final combine + explicabilite:

```bash
python src/run_final_scoring.py
```

## Dashboard MVP

```bash
streamlit run src/dashboard_app.py
```

## Documentation projet

- Plan global: `PLAN_ACTION_PROJET_THUMALIEN.md`
- Architecture MVP (Partie 0): `docs/ARCHITECTURE_MVP_PARTIE_0.md`
- Backlog priorise: `docs/BACKLOG_MVP_PRIORISE.md`
- Runbook Partie 1 (collecte): `docs/PARTIE_1_COLLECTE_BLUESKY.md`

## Regles de securite

- Ne jamais committer `.env`.
- Ne jamais stocker de mot de passe en dur dans le code.

## Notes portabilite

- Le script de collecte est `src/getapi.py` (casse importante pour Linux/macOS).
- Les artefacts locaux (env virtuel, logs, models) sont ignores par `.gitignore`.
