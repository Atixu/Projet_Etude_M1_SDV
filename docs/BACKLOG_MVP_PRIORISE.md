# Backlog MVP priorise

## Priorite P0 (bloquant MVP)
1. Securiser la configuration
- Standardiser .env.example
- Verifier absence de secrets en dur
- Ajouter consignes de rotation des credentials

2. Stabiliser la collecte Bluesky
- Valider auth createSession
- Gerer erreurs API et retries
- Persister brut en MongoDB avec dedupe

3. Rendre l'execution reproductible
- Documenter setup local
- Verifier commandes de lancement
- Aligner Airflow avec les noms de scripts reels

## Priorite P1 (coeur fonctionnel)
1. Pipeline nettoyage NLP
- Nettoyage texte FR/EN
- Enrichissement metadata
- Ecriture vers collection clean

2. Baseline fake news
- Dataset d'entrainement initial
- Modele baseline simple
- Evaluation (F1, precision, rappel)

3. Baseline emotionnelle
- Scoring emotion par post
- Verification qualitative sur echantillon

## Priorite P2 (valeur metier)
1. Score de credibilite consolide
- Regle de combinaison des signaux
- Seuils d'alerte
- Justification lisible

2. Dashboard MVP
- Vue synthese et detail
- Filtres date/langue/risque

3. Monitoring energetique
- Instrumentation runs
- Rapport comparatif

## Priorite P3 (finalisation)
1. Tests et qualite
- Tests unitaires pipelines critiques
- Tests integration collecte -> clean -> score

2. Documentation et soutenance
- Guide utilisateur
- Documentation technique
- Script de demonstration et storyboard

## Criteres de priorisation
- P0: prerequis de securite et execution
- P1: coeur fonctionnel minimum
- P2: valeur utilisateur metier
- P3: consolidation et communication
