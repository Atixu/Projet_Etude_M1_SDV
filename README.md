# Projet Thumalien — Fake News Detection on Bluesky

Projet M1 Big Data & IA — SDV 2025-2026 - William BELLON & Guillaume REAULT  
Détection automatique de désinformation sur le réseau social **Bluesky**, combinant classification NLP, analyse émotionnelle et un dashboard interactif.

---

## Sommaire

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Prérequis](#prérequis)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Lancement rapide](#lancement-rapide)
7. [Pipeline détaillé](#pipeline-détaillé)
8. [Dashboard](#dashboard)
9. [Agent IA (gratuit)](#agent-ia-gratuit)
10. [Structure du projet](#structure-du-projet)
11. [Documentation interne](#documentation-interne)
12. [Règles de sécurité](#règles-de-sécurité)
13. [Dépannage rapide](#dépannage-rapide)

---

## Vue d'ensemble

Le projet collecte des posts Bluesky via l'API officielle, les nettoie, les classe (fake / real) avec un modèle TF-IDF + Régression Logistique entraîné sur 40 000 articles labellisés (HuggingFace `GonzaloA/fake_news`), analyse leur tonalité émotionnelle (VADER + lexique custom), puis produit un **score de crédibilité final** et l'affiche dans un dashboard Streamlit.

| Étape | Script | Sortie |
|---|---|---|
| 1. Collecte | `src/getapi.py` | MongoDB `posts_raw` |
| 2. Nettoyage NLP | `src/run_nlp_cleaning.py` | MongoDB `posts_clean` |
| 3. Classification fake news | `src/run_baseline.py` | champ `credibility_score` + `alert_level` |
| 4. Émotions | `src/run_emotion_analysis.py` | champ `emotion_scores` + `dominant_emotion` |
| 5. Score final | `src/run_final_scoring.py` | champ `final_credibility_score` + `explanation_text` |
| 6. Dashboard | `src/dashboard_app.py` | http://localhost:8501 |

**Résultats obtenus sur données réelles :**
- 4 729 posts collectés, 4 618 nettoyés
- F1-score modèle baseline : **97.7%** (weighted)
- 315 alertes basses / 3 194 moyennes / 1 109 hautes

---

## Architecture

```
Bluesky API
    │  searchPosts (mots-clés FR/EN)
    ▼
MongoDB posts_raw          ← getapi.py
    │  nettoyage texte
    ▼
MongoDB posts_clean         ← run_nlp_cleaning.py
    │  TF-IDF + LogReg
    ▼
credibility_score           ← run_baseline.py
    │  VADER + lexique
    ▼
emotion_scores              ← run_emotion_analysis.py
    │  pondération 70/20/10
    ▼
final_credibility_score     ← run_final_scoring.py
    │
    ▼
Streamlit Dashboard         ← dashboard_app.py
```

**Stack technique :**
- Python 3.11+
- MongoDB 7 (via Docker)
- scikit-learn (TF-IDF + LogisticRegression)
- HuggingFace `datasets` (données d'entraînement)
- vaderSentiment (analyse de sentiment)
- Streamlit + Plotly (dashboard)
- Groq API + Llama 3.1 (chatbot IA gratuit)
- Airflow (orchestration, optionnel)

---

## Prérequis

| Outil | Version minimale | Installation |
|---|---|---|
| Python | 3.11 | https://www.python.org |
| Docker Desktop | 24+ | https://www.docker.com/products/docker-desktop |
| Git | 2.x | https://git-scm.com |

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Atixu/Projet_Etude_M1_SDV.git
cd Projet_Etude_M1_SDV
git checkout dev
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

> **Note :** `run_baseline.py` télécharge le dataset HuggingFace (~65 Mo) au premier lancement uniquement. Le modèle entraîné est ensuite sauvegardé dans `models/` (ignoré par git).

### 3. Démarrer MongoDB

```bash
docker run -d --name m1-mongo -p 27017:27017 mongo:7
```

Pour vérifier que MongoDB tourne :

```bash
docker ps | grep m1-mongo
```

---

## Configuration

### 1. Créer le fichier `.env`

**Linux / macOS :**
```bash
cp .env.example .env
```

**Windows PowerShell :**
```powershell
Copy-Item .env.example .env
```

### 2. Remplir les variables

Ouvrir `.env` et renseigner :

```dotenv
# Compte Bluesky (créer un App Password sur bsky.app → Settings → App Passwords)
BLUESKY_IDENTIFIER=ton_handle.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=bluesky

# Agent IA (gratuit)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **Important :** Ne jamais committer `.env`. Il est listé dans `.gitignore`.

---

## Lancement rapide

### Pipeline complet en une seule commande

```bash
python run_all.py
```

### Pipeline + ouverture automatique du dashboard

```bash
python run_all.py --dashboard
```

### Options disponibles

| Option | Description |
|---|---|
| `--dashboard` | Lance Streamlit à la fin du pipeline |
| `--skip-collect` | Saute la collecte (données déjà en base) |
| `--only STEP_ID` | Exécute une seule étape (`collect`, `clean`, `baseline`, `emotion`, `scoring`) |

**Exemple — relancer uniquement le scoring sans recollecte :**
```bash
python run_all.py --skip-collect --only scoring --dashboard
```

---

## Pipeline détaillé

Si tu préfères contrôler chaque étape manuellement :

### Étape 1 — Collecte Bluesky

```bash
python src/getapi.py
```

Collecte des posts via `app.bsky.feed.searchPosts` sur une liste de mots-clés (fake news, désinformation, hoax, etc.) en français et en anglais. Stocke dans MongoDB collection `posts_raw`.

### Étape 2 — Nettoyage NLP

```bash
python src/run_nlp_cleaning.py
```

Nettoie le texte brut : suppression URLs, mentions, hashtags, emojis. Conserve les accents pour le français. Stocke dans `posts_clean`.

### Étape 3 — Classification fake news

```bash
python src/run_baseline.py
```

- Télécharge `GonzaloA/fake_news` depuis HuggingFace (40 000 articles)
- Entraîne TF-IDF + LogisticRegression
- Évalue sur jeu de test (F1 = 97.7%)
- Sauvegarde le modèle dans `models/baseline_tfidf_logreg.joblib`
- Écrit `credibility_score`, `predicted_label`, `alert_level` dans `posts_clean`

### Étape 4 — Analyse émotionnelle

```bash
python src/run_emotion_analysis.py
```

Applique VADER (sentiment compound) et un lexique custom (colère, peur, joie, tristesse, surprise, humour) sur chaque post. Écrit `sentiment_compound`, `emotion_scores`, `dominant_emotion`.

### Étape 5 — Score final combiné

```bash
python src/run_final_scoring.py
```

Combine les signaux avec pondération :
- **70%** risque fake news (modèle baseline)
- **20%** risque sentiment (négatif fort → risque accru)
- **10%** risque émotion (colère/peur)

Produit `final_credibility_score` (0–100), `final_alert_level` (low / medium / high) et `explanation_text` (phrase explicative humainement lisible).

---

## Dashboard

```bash
streamlit run src/dashboard_app.py
```

Accès : http://localhost:8501

**Fonctionnalités :**
- KPIs globaux (posts analysés, alertes hautes, score moyen)
- Distribution des niveaux d'alerte
- Répartition des émotions dominantes
- Répartition FR / EN
- Série temporelle des posts
- Filtres : langue, niveau d'alerte, émotion, date, texte libre
- Vue détaillée par post avec breakdown du score
- Onglet chat IA pour questionner les tendances (Groq, modèle `llama-3.1-8b-instant`)

---

## Agent IA (gratuit)

Le dashboard inclut un onglet **🤖 Agent IA** qui répond en français à partir d'un résumé des données MongoDB:
- volume de posts,
- distribution low/medium/high,
- émotions dominantes,
- langues,
- exemples de posts à forte alerte.

### Activation

1. Créer une API key gratuite sur https://console.groq.com
2. Ajouter `GROQ_API_KEY` dans `.env`
3. Relancer Streamlit:

```bash
streamlit run src/dashboard_app.py
```

### Exemples de questions

- "Combien de posts sont en alerte high ?"
- "Quelles émotions dominent cette semaine ?"
- "Résume les tendances de désinformation en français"

---

## Structure du projet

```
Projet_Etude_M1_SDV/
├── run_all.py                  ← Lanceur unique du pipeline complet
├── requirements.txt            ← Dépendances Python
├── .env.example                ← Template de configuration
├── src/
│   ├── getapi.py               ← Collecte Bluesky → MongoDB
│   ├── nlp_cleaning.py         ← Module de nettoyage texte
│   ├── run_nlp_cleaning.py     ← Batch nettoyage posts_raw → posts_clean
│   ├── run_baseline.py         ← Entraînement + scoring fake news
│   ├── emotion_analysis.py     ← Module analyse émotionnelle
│   ├── run_emotion_analysis.py ← Batch analyse émotions
│   ├── run_final_scoring.py    ← Score final + explainabilité
│   └── dashboard_app.py        ← Dashboard Streamlit
├── models/                     ← Modèles entraînés (ignoré par git)
├── airflow/                    ← Orchestration Airflow (optionnel)
│   ├── docker-compose.yaml
│   └── dags/run_pipeline.py
├── docs/
│   ├── ARCHITECTURE_MVP_PARTIE_0.md
│   ├── BACKLOG_MVP_PRIORISE.md
│   └── PARTIE_1_COLLECTE_BLUESKY.md
├── PLAN_ACTION_PROJET_THUMALIEN.md
└── HANDOVER_CONTEXT.md         ← Contexte complet pour nouveaux contributeurs
```

---

## Documentation interne

| Fichier | Contenu |
|---|---|
| [HANDOVER_CONTEXT.md](HANDOVER_CONTEXT.md) | Onboarding complet : contexte, décisions, état du projet |
| [PLAN_ACTION_PROJET_THUMALIEN.md](PLAN_ACTION_PROJET_THUMALIEN.md) | Plan en 9 parties avec KPIs et livrables |
| [docs/ARCHITECTURE_MVP_PARTIE_0.md](docs/ARCHITECTURE_MVP_PARTIE_0.md) | Diagramme d'architecture et choix techniques |
| [docs/BACKLOG_MVP_PRIORISE.md](docs/BACKLOG_MVP_PRIORISE.md) | Backlog priorisé |
| [docs/PARTIE_1_COLLECTE_BLUESKY.md](docs/PARTIE_1_COLLECTE_BLUESKY.md) | Runbook collecte Bluesky |

---

## Règles de sécurité

- Ne **jamais** committer `.env` (listé dans `.gitignore`)
- Ne **jamais** écrire de mot de passe ou token en dur dans le code
- Utiliser des **App Passwords** Bluesky (révocables), jamais le mot de passe principal
- Les credentials MongoDB en production doivent utiliser l'authentification

---

## Dépannage rapide

- Erreur MongoDB `ServerSelectionTimeoutError`:

```bash
docker start m1-mongo
```

- Docker daemon non disponible sous Windows:
    ouvrir Docker Desktop puis relancer la commande.

- L'onglet IA affiche une erreur modèle Groq:
    vérifier que `GROQ_API_KEY` est bien défini, puis utiliser le modèle actuel déjà configuré (`llama-3.1-8b-instant`).
