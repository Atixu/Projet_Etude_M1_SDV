# Plan d'action - Projet Thumalien (M1 Data & IA)

## 1) Contexte et problematique
Les reseaux sociaux accelerent la diffusion d'information, mais aussi la propagation de fake news.
Le projet vise a analyser automatiquement les messages publies sur Bluesky pour :
- identifier rapidement les contenus douteux ou trompeurs,
- evaluer leur impact emotionnel (colere, peur, humour, etc.),
- fournir un outil d'aide au fact-checking.

Problemes cibles :
- volume d'information trop eleve pour une moderation humaine,
- propagation des fake news plus rapide que les dementis,
- outils automatises souvent limites a l'anglais,
- faible prise en compte de l'impact emotionnel et energetique.

Enjeux metier et societal :
- aider journalistes, associations et citoyens,
- produire des scores de credibilite exploitables,
- integrer une demarche Green IT.

## 2) Objectifs du projet
- Developper une pipeline NLP pour detecter les fake news sur Bluesky.
- Generer des indicateurs clairs (score de credibilite, tonalite emotionnelle).
- Garantir la transparence via une explication des decisions.
- Suivre la consommation energetique (entrainement et inference).

## 3) Parties prenantes et besoins
- Utilisateurs finaux : interface simple, score de credibilite, alertes.
- Fact-checkers : details de classification, justification du score.
- Equipe technique : pipeline fiable, scalable, monitorable.
- Direction/client : valeur societale, MVP concret, resultat demonstrable.

## 4) Fonctionnalites attendues
1. Collecte des donnees Bluesky (FR/EN) et stockage brut.
2. Pretraitement NLP (nettoyage, tokenisation, embeddings).
3. Detection fake news (classification + score).
4. Analyse emotionnelle (tonalites + visualisation).
5. Dashboard utilisateur (vue simple + graphiques).
6. Suivi energetique (CPU/GPU + rapport).

## 5) Stack technique conseillee
- Collecte : API Bluesky, Python requests.
- NLP : NLTK, spaCy, Transformers.
- Classification : baseline scikit-learn, puis BERT/RoBERTa.
- Emotions : baseline VADER, puis modele specialise.
- Stockage : PostgreSQL et/ou MongoDB.
- Visualisation : Streamlit ou Dash.
- Energie : CodeCarbon, MLCO2.
- Infra : Docker, execution locale/Cloud etudiant.

## 6) Innovations attendues
- Explicabilite IA (mots influents / facteurs de decision).
- Couplage fake news + emotions.
- Dashboard pedagogique et operationnel.
- Monitoring energetique integre au cycle ML.
- Vision scalable (Spark/Kafka en evolution future).

## 7) Repartition des roles (proposition)
- Etudiant 1 - Data Engineer : API, stockage, ETL.
- Etudiant 2 - Data Scientist : NLP, modelisation fake news.
- Etudiant 3 - Analyste IA : emotions, explicabilite, dashboard.
- Etudiant 4 - Green IT : suivi energetique, qualite code.

## 8) Livrables attendus
- MVP fonctionnel de bout en bout.
- Documentation technique.
- Guide utilisateur.
- Video de demonstration.

## 9) Bonnes pratiques et KPIs
Bonnes pratiques :
- versionner le code,
- documenter chaque etape de pipeline,
- ecrire des tests unitaires et integration,
- tracer les performances techniques et energetiques.

KPIs :
- F1-score,
- taux de faux positifs/faux negatifs,
- temps moyen d'analyse,
- consommation energetique par run.

---

## 10) Plan d'action decoupe en parties

### Partie 0 - Cadrage et socle technique
Objectif : verrouiller les regles du projet et l'environnement.

Taches :
- definir le perimetre MVP FR/EN,
- fixer les KPIs cibles,
- securiser les secrets (aucun mot de passe en dur),
- valider l'architecture cible (Airflow + Kedro + DB + Dashboard).

Livrables :
- note d'architecture (1 page),
- backlog priorise,
- convention de configuration (fichier .env.example).

Critere de validation :
- installation et lancement reproductibles en local.

### Partie 1 - Collecte Bluesky et stockage brut
Objectif : collecter des posts de maniere robuste.

Taches :
- implementer extraction API avec pagination,
- gerer les erreurs et retries,
- stocker les objets bruts avec identifiant unique,
- logguer volumes et dates de collecte.

Livrables :
- collection/table raw alimentee,
- job executable manuellement et via orchestration.

Critere de validation :
- plusieurs runs sans doublons critiques.

### Partie 2 - Pretraitement NLP
Objectif : transformer le brut en donnees propres pour le ML.

Taches :
- nettoyage texte (URL, mentions, hashtags, emojis),
- normalisation linguistique FR/EN,
- enrichissement metadata (langue, longueur, etc.),
- production dataset clean versionne.

Livrables :
- dataset clean exploitable,
- rapport qualite donnees.

Critere de validation :
- pipeline stable et donnees coherentes.

### Partie 3 - Baseline fake news
Objectif : obtenir un modele de reference mesurable.

Taches :
- construire baseline simple (ex. TF-IDF + classifieur),
- definir split train/validation/test,
- mesurer F1, precision, rappel, matrice confusion,
- documenter limites et biais observes.

Livrables :
- modele baseline entraine,
- rapport d'evaluation initial.

Critere de validation :
- performance mesurable et reproductible.

### Partie 4 - Analyse emotionnelle
Objectif : enrichir les contenus avec des scores emotionnels.

Taches :
- baseline emotionnelle,
- attribution de scores par post,
- verification qualitative sur echantillon,
- agregation par periode/theme.

Livrables :
- dataset enrichi emotions,
- indicateurs de tonalite.

Critere de validation :
- scores exploitables dans le dashboard.

### Partie 5 - Explicabilite et score de credibilite final
Objectif : rendre les decisions comprensibles.

Taches :
- definir un score combine (fake news + emotions + confiance),
- fournir justification textuelle par prediction,
- fixer seuils d'alerte (faible/moyen/eleve).

Livrables :
- score de credibilite normalise,
- bloc d'explication lisible pour fact-checking.

Critere de validation :
- chaque resultat est interpretable.

### Partie 6 - Dashboard MVP
Objectif : visualiser les resultats de bout en bout.

Taches :
- vue synthese (volume, risque, emotions),
- vue detail (post, score, justification),
- filtres (date, langue, niveau de risque).

Livrables :
- dashboard operationnel,
- demonstration complete collecte -> visualisation.

Critere de validation :
- un utilisateur non technique comprend le resultat rapidement.

### Partie 7 - Monitoring energetique
Objectif : repondre a l'axe Green IT.

Taches :
- instrumenter les runs (entrainement/inference),
- comparer au moins 2 configurations,
- produire recommandations d'optimisation.

Livrables :
- rapport energie par etape,
- mesures comparatives.

Critere de validation :
- indicateurs energie integres aux livrables finaux.

### Partie 8 - Industrialisation et soutenance
Objectif : fiabiliser et presenter un MVP solide.

Taches :
- tests unitaires/integration,
- gestion d'erreurs et observabilite,
- documentation technique + guide utilisateur,
- preparation script de demo et trame de soutenance.

Livrables :
- MVP complet,
- docs,
- video de demonstration.

Critere de validation :
- demo stable et reproductible.

## 11) Planning suggere (6 sprints)
- Sprint 1 : Parties 0 et 1
- Sprint 2 : Partie 2
- Sprint 3 : Partie 3
- Sprint 4 : Parties 4 et 5
- Sprint 5 : Partie 6
- Sprint 6 : Parties 7 et 8

## 12) Regle de fonctionnement avec Copilot (travail partie par partie)
Pour chaque partie :
1. Definition precise du scope.
2. Liste des fichiers a creer/modifier.
3. Implementation.
4. Verification/tests.
5. Mini compte rendu (ce qui est fait, reste a faire, risques).