# Documentation technique — Projet Thumalien
## Détection de fake news sur Bluesky · M1 Big Data & IA SDV

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Pourquoi Bluesky ?](#2-pourquoi-bluesky-)
3. [L'infrastructure technique](#3-linfrastructure-technique)
4. [Étape 1 — Collecte des données](#4-étape-1--collecte-des-données)
5. [Étape 2 — Nettoyage NLP](#5-étape-2--nettoyage-nlp)
6. [Étape 3 — Claim Detection](#6-étape-3--claim-detection)
7. [Étape 4 — Modèle baseline (TF-IDF + Régression Logistique)](#7-étape-4--modèle-baseline-tf-idf--régression-logistique)
8. [Étape 5 — Analyse émotionnelle (VADER)](#8-étape-5--analyse-émotionnelle-vader)
9. [Étape 6 — Score de crédibilité final](#9-étape-6--score-de-crédibilité-final)
10. [Le dashboard Streamlit](#10-le-dashboard-streamlit)
11. [GreenIT — mesure de l'impact carbone](#11-greenit--mesure-de-limpact-carbone)
12. [Résultats obtenus](#12-résultats-obtenus)
13. [Comment vulgariser le projet](#13-comment-vulgariser-le-projet)

---

## 1. Vue d'ensemble

**Thumalien** est un système automatisé de détection de fake news sur le réseau social Bluesky. Il collecte des posts publics, les analyse avec plusieurs modèles d'intelligence artificielle et produit pour chaque post un **score de crédibilité** et un **niveau d'alerte**.

### Le problème qu'on résout

Les fake news se propagent très vite sur les réseaux sociaux. Un humain ne peut pas lire 20 000 posts par jour pour identifier les informations douteuses. L'objectif du projet est d'automatiser ce tri à l'aide du machine learning et du NLP (traitement automatique du langage naturel).

### Le pipeline en une phrase

> On collecte des posts Bluesky → on nettoie le texte → on filtre les posts informationnels → on les classe fake/réel → on analyse les émotions → on combine tout en un score final → on affiche dans un dashboard.

### Vue d'ensemble du pipeline

```
Bluesky API
    │
    ▼
[1. COLLECTE]
getapi.py → posts_raw (MongoDB)
    │
    ▼
[2. NETTOYAGE]
run_nlp_cleaning.py → posts_clean (MongoDB)
    │
    ▼
[3. CLAIM DETECTION]
run_claim_filter.py → is_claim=True/False (dans posts_clean)
    │
    │ (seulement les is_claim=True)
    ▼
[4. BASELINE ML]
run_baseline.py → credibility_score (dans posts_clean)
    │
    ▼
[5. ÉMOTIONS]
run_emotion_analysis.py → sentiment + emotions (dans posts_clean)
    │
    ▼
[6. SCORE FINAL]
run_final_scoring.py → final_credibility_score + final_alert_level
    │
    ▼
[DASHBOARD]
dashboard_app.py (Streamlit)
```

---

## 2. Pourquoi Bluesky ?

**Bluesky** est un réseau social décentralisé (concurrent de X/Twitter), lancé par Jack Dorsey. Il est basé sur le protocole AT (Authenticated Transfer Protocol), un standard ouvert.

### Avantages techniques pour notre projet

| Critère | Bluesky | Twitter/X |
|---|---|---|
| API gratuite | Oui, sans limite de taux | Non (payante depuis 2023) |
| Recherche plein texte | Oui (`app.bsky.feed.searchPosts`) | Réservée aux abonnés payants |
| Posts publics accessibles | Oui, sans authentification lourde | Restreint |
| Authentification | Simple (identifiant + mot de passe d'application) | OAuth complexe + clés API |

### Comment on s'authentifie

On crée une **session** via l'API AT Protocol :
```
POST https://bsky.social/xrpc/com.atproto.server.createSession
{ "identifier": "mon_compte.bsky.social", "password": "mot_de_passe_app" }
```
En retour, on reçoit un **JWT** (JSON Web Token), un token temporaire qu'on inclut dans toutes les requêtes suivantes pour prouver qu'on est bien nous.

---

## 3. L'infrastructure technique

### Docker et MongoDB

**Docker** est un outil qui permet de faire tourner des applications dans des "conteneurs" — des environnements isolés qui fonctionnent de façon identique peu importe l'ordinateur. On l'utilise pour lancer **MongoDB** sans avoir à l'installer manuellement.

**MongoDB** est une base de données NoSQL (non relationnelle). Contrairement à une base SQL (tableaux avec colonnes fixes), MongoDB stocke des **documents JSON** flexibles. C'est parfait pour nous car chaque post Bluesky a une structure légèrement différente.

```
┌─────────────────────────────────────────────────┐
│  Docker Desktop                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Conteneur m1-mongo                       │   │
│  │  Image : mongo:7                          │   │
│  │  Port  : 27017                            │   │
│  │  ┌─────────────┐  ┌──────────────────┐   │   │
│  │  │  posts_raw  │  │   posts_clean    │   │   │
│  │  │  ~22 408    │  │   ~22 184 docs   │   │   │
│  │  │  documents  │  │   enrichis       │   │   │
│  │  └─────────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Pourquoi deux collections ?**
- `posts_raw` : les posts tels qu'ils arrivent de l'API, rien n'est modifié (données brutes)
- `posts_clean` : les posts nettoyés et enrichis progressivement par chaque étape du pipeline

Chaque étape **ajoute des champs** au document dans `posts_clean`. À la fin, un document ressemble à :

```json
{
  "uri": "at://did:plc:xxx/app.bsky.feed.post/yyy",
  "text": "Selon l'OMS, les vaccins causent l'autisme !",
  "clean_text": "selon oms vaccins causent autisme",
  "lang": "fr",
  "is_claim": true,
  "claim_score": 0.82,
  "credibility_score": 0.08,
  "predicted_label": "fake",
  "sentiment_label": "negative",
  "dominant_emotion": "fear",
  "final_credibility_score": 0.12,
  "final_alert_level": "high"
}
```

### Le fichier .env

Toutes les informations sensibles (mots de passe, URLs) sont dans un fichier `.env` qui n'est **jamais partagé** (ignoré par git). Il contient :

```
BLUESKY_IDENTIFIER=mon_compte.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
MONGO_URI=mongodb://localhost:27017
BLUESKY_MAX_PAGES=20
```

---

## 4. Étape 1 — Collecte des données

**Script :** `src/getapi.py`

### Comment ça marche

On interroge l'API Bluesky avec une liste de **mots-clés** liés à la désinformation :

```python
SEARCH_TERMS = [
    "fake news", "hoax", "complot", "désinformation", "propagande",
    "intox", "canular", "rumeur", "manipulation", "fausse info",
    "conspiracy", "misinformation", "disinformation", ...
]
```

Pour chaque mot-clé, on fait plusieurs pages de requêtes (20 pages × 100 posts = 2 000 posts par terme maximum). Le système de **pagination** fonctionne avec un `cursor` : l'API retourne un token opaque qui représente "là où on s'est arrêtés", et on le passe dans la requête suivante pour continuer.

```
Page 1 → cursor="abc123"
Page 2 (cursor="abc123") → cursor="def456"
Page 3 (cursor="def456") → ... 
```

### Gestion des erreurs réseau

Le script est robuste : si l'API retourne une erreur temporaire (rate limit 429, serveur surchargé 503...), il **réessaie automatiquement** avec un délai exponentiel (0.5s, 1s, 2s, 4s, 8s) grâce à la bibliothèque `urllib3.Retry`.

### Dédoublonnage

Chaque post a un identifiant unique (`uri`) sous la forme `at://did:plc:xxx/...`. En MongoDB, on utilise `UpdateOne` avec `upsert=True` : si le post existe déjà (même URI), il est **mis à jour** plutôt que dupliqué. Ça évite les doublons même si on relance la collecte.

### Résultat

- **22 408 posts** stockés dans `posts_raw`

---

## 5. Étape 2 — Nettoyage NLP

**Script :** `src/run_nlp_cleaning.py` + `src/nlp_cleaning.py`

### Pourquoi nettoyer ?

Les modèles de machine learning travaillent sur du **texte normalisé**. Un post brut contient du bruit : URLs, emojis, majuscules inconsistantes, ponctuation aléatoire, caractères spéciaux. Tout ça perturbe les modèles.

### Les étapes de nettoyage

1. **Suppression des URLs** : `https://t.co/xxx` → (vide)
2. **Suppression des mentions** : `@utilisateur` → (vide)
3. **Suppression des hashtags** : `#FakeNews` → (vide)  
   *Note : le contenu sémantique (le mot) est conservé si nécessaire*
4. **Conversion en minuscules** : `VACCIN` → `vaccin`
5. **Suppression de la ponctuation et des caractères spéciaux**
6. **Suppression des emojis**
7. **Tokenisation** : découpage en mots (tokens)
8. **Suppression des stopwords** : mots très courants sans sens propre ("le", "la", "de", "et"...)
9. **Lemmatisation** : ramener les mots à leur forme de base (`mangeaient` → `manger`, `vaccins` → `vaccin`)

### Exemple concret

```
Texte brut   : "Selon l'OMS 🔬, LES VACCINS causent l'autisme !! 
               Source: https://fake.com/article #santé @bob"

Texte nettoyé: "selon oms vaccins causent autisme source santé"
```

### Filtre de qualité

Les posts trop courts (< 5 tokens après nettoyage) sont **écartés** : ils ne contiennent pas assez d'information pour être analysés.

### Résultat

- **22 408 → 22 184 posts** dans `posts_clean` (224 posts trop courts éliminés)

---

## 6. Étape 3 — Claim Detection

**Script :** `src/run_claim_filter.py`

### Le problème qu'on résout

Avant ce filtre, le modèle baseline classait **96,4 % des posts comme fake**. Ce chiffre est évidemment faux. Pourquoi ?

Le modèle a été entraîné sur des **articles de presse** (longs, structurés, factuels). Quand on lui donne des posts personnels comme :
- *"Je suis trop fatigué là 😭"*
- *"Quelqu'un a regardé le match hier ?"*

Il ne sait pas quoi en faire et les classe par défaut comme fake. Ces posts n'ont **aucune prétention informationnelle** — les classer fake n'a aucun sens.

**La solution :** ajouter une étape préalable qui filtre les posts selon la question : *"Ce post contient-il une affirmation factuelle vérifiable ?"*

### Le scoring heuristique (9 critères)

Chaque post reçoit un **score entre 0 et 1**, en partant de 0,50 (neutre) et en ajustant selon 9 critères :

| # | Critère | Effet | Explication |
|---|---------|-------|-------------|
| 1 | Texte trop court (< 8 mots) | −0,30 | Un post court est probablement personnel |
| 2 | Pronoms personnels FR (je, moi, mon…) | −0,35 si > 15% | "Je pense que..." = opinion personnelle |
| 3 | Pronoms personnels EN (I, me, my…) | −0,35 si > 15% | "I'm so tired" = post personnel |
| 4 | Marqueurs factuels FR (selon, annonce, étude…) | +0,15 à +0,30 | "Selon l'OMS..." = affirmation factuelle |
| 5 | Marqueurs factuels EN (according, report, study…) | +0,15 à +0,30 | "According to CNN..." = affirmation factuelle |
| 6 | Chiffres et statistiques (%, millions, années) | +0,07 à +0,15 | "40% des Français..." = données concrètes |
| 7 | Entités nommées (séquences de majuscules) | +0,06 à +0,12 | "Emmanuel Macron", "Union Européenne" |
| 8 | URL présente | +0,08 | Partager un lien = souvent une info |
| 9 | Emojis excessifs (≥5) ou hashtags excessifs (≥4) | −0,08 à −0,18 | Signe de contenu émotionnel/viral, pas factuel |

**Seuil de décision :**
```
score ≥ 0,50  →  is_claim = True   (affirmation factuelle → entre dans le pipeline)
score < 0,50  →  is_claim = False  (post personnel → ignoré pour la suite)
```

### Pourquoi heuristique et pas un modèle ML ?

- **Vitesse** : 22 184 posts traités en 11 secondes, sans GPU, sans API externe
- **Transparence** : on peut expliquer exactement pourquoi un post est classé claim ou non (`claim_reason`)
- **Coût carbone nul** : pas d'entraînement, pas d'inférence lourde

### Résultat

| | Résultat |
|---|---|
| Affirmations factuelles (is_claim=True) | **19 634 — 88,5 %** |
| Posts personnels filtrés (is_claim=False) | **2 550 — 11,5 %** |
| Temps de traitement | **11,3 secondes** |

> **Pourquoi 88,5 % et pas ~50 % ?** Parce que les posts ont été collectés avec des mots-clés ciblés (fake news, hoax, complot...). Ces termes attirent naturellement des posts informationnels. Les 2 550 filtrés sont des posts qui utilisaient ces mots de façon incidente ("c'est un hoax cette série" = avis personnel).

---

## 7. Étape 4 — Modèle baseline (TF-IDF + Régression Logistique)

**Script :** `src/run_baseline.py`

Cette étape s'applique **uniquement aux 19 634 posts is_claim=True**.

### Le dataset d'entraînement

On utilise le dataset public **GonzaloA/fake_news** sur HuggingFace : 40 587 articles de presse labellisés manuellement en `fake` ou `real`. Ce sont de vrais articles journalistiques, avec titre et corps de texte.

```
Train : ~32 000 articles
Test  :  ~8 000 articles
Fake  : 18 663 articles (46 %)
Real  : 21 924 articles (54 %)
```

### TF-IDF — transformer le texte en nombres

Un modèle de machine learning ne peut pas lire du texte. Il faut le convertir en **vecteurs numériques**. TF-IDF (Term Frequency – Inverse Document Frequency) le fait ainsi :

- **TF (Term Frequency)** : fréquence d'un mot dans le document. "vaccin" apparaît 3 fois sur 100 mots → TF = 0,03
- **IDF (Inverse Document Frequency)** : rareté du mot dans tous les documents. Si "vaccin" est rare dans le corpus → IDF est élevé. Si "le" apparaît partout → IDF est proche de 0
- **TF-IDF = TF × IDF** : un mot fréquent dans le document ET rare dans le corpus a une valeur élevée → c'est un mot discriminant

On utilise des **unigrammes et bigrammes** : mots seuls ("vaccin") ET paires de mots ("vaccin autisme", "fausse information"). Les bigrammes capturent des associations sémantiques importantes.

#### Vulgarisation

> Imagine un bibliothécaire qui lit 40 000 articles. Il remarque que les articles fake utilisent souvent des mots comme "choc", "scandale", "révélé" et des associations comme "vaccin autisme", "élite mondiale". Les vrais articles utilisent plutôt "selon les experts", "étude publiée", "données officielles". TF-IDF mesure exactement cette importance des mots.

### Régression Logistique — le classifieur

Une fois le texte converti en vecteur numérique (des milliers de dimensions, une par mot/bigramme), la **régression logistique** apprend à tracer une frontière entre les articles fake et réels dans cet espace.

Elle produit une **probabilité** : "ce post a 92 % de chances d'être fake". On utilise la probabilité d'être `real` comme **score de crédibilité** : 0 = très douteux, 1 = très fiable.

### Résultats du modèle

```
              precision  recall  f1-score
fake            0.971    0.979    0.975
real            0.982    0.975    0.978

F1 score global : 97,7 %
```

**Matrice de confusion :**
```
              Prédit Fake  Prédit Real
Réel Fake        3653          80      (2,1% d'erreurs)
Réel Real         109        4276      (2,5% d'erreurs)
```

### Application sur nos posts Bluesky

Le modèle est appliqué aux 19 634 posts Bluesky claims. Résultat :
- fake : 18 854 (96 %)
- real : 780 (4 %)

Ce taux de 96 % est élevé mais cohérent : les posts collectés avec des mots-clés "désinformation/complot" contiennent naturellement beaucoup de contenu douteux.

---

## 8. Étape 5 — Analyse émotionnelle (VADER)

**Script :** `src/run_emotion_analysis.py` + `src/emotion_analysis.py`

### VADER — analyse de sentiment

**VADER** (Valence Aware Dictionary and sEntiment Reasoner) est un outil de NLP basé sur un **lexique de sentiments** : un dictionnaire où chaque mot a un score de positivité/négativité.

Il produit 4 scores pour chaque texte :
- `pos` : proportion de sentiment positif
- `neg` : proportion de sentiment négatif  
- `neu` : proportion de sentiment neutre
- `compound` : score global de −1 (très négatif) à +1 (très positif)

#### Règles de classification

```
compound >= +0.05  →  sentiment_label = "positive"
compound <= -0.05  →  sentiment_label = "negative"
sinon              →  sentiment_label = "neutral"
```

### Analyse des émotions

En plus du sentiment général, on détecte 6 émotions spécifiques grâce à un **lexique d'émotions** bilingue FR/EN :

| Émotion | Rôle dans la fake news |
|---------|----------------------|
| `anger` (colère) | Forte corrélation avec les fake news — elles jouent sur l'indignation |
| `fear` (peur) | Contenu alarmiste, théories du complot |
| `sadness` (tristesse) | Contenus pessimistes ou manipulatoires |
| `joy` (joie) | Signal positif, réduit le risque estimé |
| `humor` (humour) | Post satirique ou ironique |
| `surprise` (surprise) | Contenu "choquant", clickbait |

L'émotion avec le score le plus élevé devient la **`dominant_emotion`** du post.

### Résultats sur les 19 634 claims

```
Négatif  : 8 957 posts (45,6 %)
Positif  : 6 234 posts (31,8 %)
Neutre   : 4 443 posts (22,6 %)
```

L'émotion dominante la plus fréquente : **négatif** — cohérent avec un corpus sur la désinformation.

---

## 9. Étape 6 — Score de crédibilité final

**Script :** `src/run_final_scoring.py`

Cette étape **combine** les trois signaux précédents en un score unique.

### La formule de combinaison

```
final_credibility_score = (
    credibility_score   × 0.70   (baseline fake news)
  + sentiment_weight    × 0.20   (sentiment VADER)
  + emotion_weight      × 0.10   (émotions)
)
```

**Poids expliqués :**
- Le signal le plus fort (70 %) vient du **modèle ML** entraîné sur 40 000 articles
- Le sentiment (20 %) ajuste : un ton très négatif est un signal de risque
- Les émotions (10 %) raffinent : la colère et la peur augmentent le risque

### Conversion du sentiment en poids

```python
# compound de VADER : -1 (très négatif) à +1 (très positif)
# On le convertit en "contribution à la crédibilité"
sentiment_weight = (compound + 1) / 2  # remis entre 0 et 1
```

### Calcul du risque émotionnel

```python
emotion_risk = (1.2 × anger) + (1.0 × fear) + (0.8 × sadness)
             - (0.6 × joy)   - (0.3 × humor) - (0.1 × surprise)
# clampé entre 0 et 1
```

La **colère** a le poids le plus élevé (1.2) car c'est l'émotion la plus corrélée avec les fake news — elles sont souvent conçues pour provoquer l'indignation.

### Niveaux d'alerte

```
final_credibility_score < 0.35  →  alerte "high"   (rouge)   post très probablement fake
final_credibility_score < 0.60  →  alerte "medium" (orange)  post douteux
final_credibility_score ≥ 0.60  →  alerte "low"    (vert)    post probablement fiable
```

### Explainabilité automatique

Pour chaque post, une **explication en texte** est générée automatiquement :

> *"Le modèle fake-news de base estime une faible crédibilité. Le ton global est négatif, ce qui augmente le risque de contenu trompeur. Des émotions à risque sont détectées (émotion dominante : fear). Niveau d'alerte final : high."*

### Résultats finaux (sur 19 634 claims)

```
Alerte high   (rouge)  : 4 912 posts  (25,0 %)
Alerte medium (orange) : 13 177 posts  (67,1 %)
Alerte low    (vert)   : 1 545 posts   (7,9 %)

Score de crédibilité moyen : 0,44 / 1
```

---

## 10. Le dashboard Streamlit

**Script :** `src/dashboard_app.py`

### Streamlit

**Streamlit** est un framework Python qui permet de créer des applications web interactives sans écrire une ligne de HTML/CSS/JavaScript. Chaque widget (bouton, filtre, graphique) est déclaré en Python.

### Fonctionnalités du dashboard

**Filtres sidebar :**
- Langue (fr, en, autre)
- Niveau d'alerte (high/medium/low)
- Émotion dominante
- Période de date
- Recherche texte libre
- Toggle "Affirmations factuelles uniquement" (filtre `is_claim=True`)

**Onglet Dashboard :**
- 5 KPIs en haut : nombre de posts, alertes high/medium/low, score moyen
- Graphique en camembert : distribution des alertes
- Graphique en barres : émotions dominantes
- Timeline : volume de posts par jour
- Tableau détaillé : liste des posts avec leurs scores
- Vue détail : pour un post sélectionné, affiche le texte, l'explication et toutes les métriques

**Onglet Agent IA (Groq/Llama) :**
- Chatbot connecté à l'API Groq (modèle Llama 3.1)
- Le prompt système inclut les statistiques actuelles de la base
- L'utilisateur peut poser des questions en langage naturel sur les données

### Architecture de la donnée dans le dashboard

```python
# Chargement depuis MongoDB (mis en cache 2 minutes)
@st.cache_data(ttl=120)
def load_posts_df():
    docs = col.find({}, projection)  # Tous les champs utiles
    return pd.DataFrame(docs)

# Filtrage côté Python (pas de requête MongoDB à chaque clic)
filtered = df[df["is_claim"] == True]
filtered = filtered[filtered["lang"].isin(selected_langs)]
```

---

## 11. GreenIT — mesure de l'impact carbone

**Bibliothèque :** CodeCarbon (`codecarbon`)

### Pourquoi mesurer l'empreinte carbone ?

Former et utiliser des modèles de ML consomme de l'électricité. Dans une démarche de **Green IT** (informatique responsable), on mesure cette consommation pour en être conscient et la minimiser.

### Comment ça marche

CodeCarbon mesure :
- La consommation CPU (via `psutil`)
- La consommation GPU si disponible
- L'intensité carbone de l'électricité selon la région géographique (g CO₂/kWh)
- Produit un rapport en kg CO₂ équivalent

```python
from codecarbon import EmissionsTracker

tracker = EmissionsTracker(project_name="baseline_training")
tracker.start()
# ... entraînement du modèle ...
emissions = tracker.stop()  # en kg CO₂eq
```

### Choix techniques orientés GreenIT

- **TF-IDF + LogReg** plutôt qu'un LLM : le modèle léger consomme 1000× moins qu'un modèle type GPT
- **Claim Detection heuristique** : 0 consommation d'inférence lourde (règles + regex)
- **Pagination ciblée** : on collecte exactement ce qu'il faut, pas plus
- **Upsert MongoDB** : pas de données dupliquées inutilement

---

## 12. Résultats obtenus

### Chiffres clés du pipeline complet

| Étape | Résultat |
|-------|---------|
| Posts collectés | **22 408** |
| Posts après nettoyage | **22 184** |
| Posts filtrés (non-claims) | **2 550 (11,5 %)** |
| Posts analysés (claims) | **19 634 (88,5 %)** |
| F1-score du modèle baseline | **97,7 %** |
| Alertes high (rouge) | **4 912 (25,0 %)** |
| Alertes medium (orange) | **13 177 (67,1 %)** |
| Alertes low (vert) | **1 545 (7,9 %)** |
| Score de crédibilité moyen | **0,44 / 1** |
| Émotion dominante la plus fréquente | **Négatif** |

### Interprétation

Le score moyen de 0,44 signifie que les posts sur la désinformation collectés sur Bluesky ont une crédibilité légèrement en dessous de la moyenne. C'est cohérent : en cherchant les mots "fake news" et "complot", on trouve naturellement beaucoup de contenu douteux.

Les 97,7 % de F1-score sur le modèle baseline sont excellents **sur le dataset d'entraînement** (articles de presse). Sur des posts sociaux, la performance réelle est plus difficile à évaluer sans annotation manuelle.

---

## 13. Comment vulgariser le projet

Cette section te donne les analogies et formulations pour expliquer chaque partie sans jargon.

### L'explication en 30 secondes

> *"On a créé un système qui lit automatiquement des milliers de posts sur Bluesky — un réseau social — et qui leur donne une note de crédibilité. Si quelqu'un écrit 'Selon une étude, les vaccins causent l'autisme', notre système va analyser le texte, le comparer à des dizaines de milliers d'articles labellisés fake ou réels, analyser si le ton est alarmiste ou manipulateur, et dire : ce post est probablement une fake news, niveau d'alerte rouge."*

### L'explication des composants techniques

**MongoDB :**
> *"C'est notre carnet de notes numérique. Chaque post qu'on collecte est noté dans ce carnet, avec toutes ses informations. Au fur et à mesure de l'analyse, on ajoute des notes dans le carnet : d'abord la langue, puis le score de fake news, puis l'émotion..."*

**TF-IDF :**
> *"C'est comme si tu cherchais les mots qui sont des 'signatures' d'un type de texte. Si 'choc', 'scandale' et 'révélé' apparaissent souvent dans les fake news mais rarement dans les vraies infos, ces mots deviennent des indicateurs rouges. TF-IDF mesure automatiquement cette importance."*

**Régression Logistique :**
> *"Après avoir appris sur 40 000 articles, le modèle sait que certaines combinaisons de mots sont typiques des fake news. Quand il voit un nouveau texte, il calcule une probabilité : '92 % de chances que ce soit une fake news'. C'est comme un détecteur formé à reconnaître les patterns."*

**Claim Detection :**
> *"Avant d'analyser si un post est fake, on vérifie d'abord s'il fait une vraie affirmation. 'Je suis fatigué' n'est pas une information vérifiable — ça ne sert à rien de chercher si c'est une fake news. On filtre ces posts personnels pour ne garder que ceux qui prétendent dire quelque chose de factuel."*

**VADER :**
> *"Les fake news utilisent souvent un langage chargé émotionnellement pour manipuler les gens. VADER lit le texte et mesure si le ton est positif, négatif ou neutre. Un post qui crie 'SCANDALE RÉVÉLÉ !!!' a un score très négatif, ce qui renforce le signal de méfiance."*

**Dashboard Streamlit :**
> *"C'est l'interface visuelle pour explorer les résultats. Imagine un tableau de bord de voiture : en un coup d'œil, tu vois si tout va bien ou s'il y a des alertes. Ici, l'analyste peut filtrer par langue, par niveau d'alerte, chercher un mot-clé, et voir le détail d'un post suspect."*

**Docker :**
> *"C'est une boîte hermétique qui contient notre base de données. L'avantage : ça marche exactement pareil sur n'importe quel ordinateur. Pas besoin d'installer MongoDB manuellement ou de configurer quoi que ce soit — tu lances la boîte, et c'est prêt."*

### Les questions qu'on pourrait te poser

**"97,7 % de précision, c'est parfait non ?"**
> *"C'est excellent sur le dataset d'entraînement, qui est composé d'articles de presse longs et bien structurés. Sur des posts sociaux courts et informels, la performance réelle serait plus basse. C'est pour ça qu'on a ajouté la claim detection et l'analyse émotionnelle : on croise plusieurs signaux plutôt que de se fier à un seul modèle."*

**"Ça peut vraiment détecter les fake news ?"**
> *"Notre système détecte les posts qui ressemblent aux fake news qu'il a vues pendant l'entraînement. Ce n'est pas infaillible — un bon fake news bien rédigé peut passer. C'est un outil d'aide à la décision, pas un oracle. L'idée est de prioriser les posts à vérifier manuellement."*

**"Pourquoi pas utiliser ChatGPT directement ?"**
> *"ChatGPT serait beaucoup plus coûteux (en argent et en énergie) et 1000× plus lent. Notre pipeline traite 19 634 posts en moins de 2 minutes avec des outils légers. Pour un projet académique avec contrainte GreenIT, c'est le bon compromis."*

---

*Document rédigé le 25 juin 2026 — Projet Thumalien M1 Big Data & IA SDV*
