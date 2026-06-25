# Claim Detection — Filtre d'affirmations factuelles

## Pourquoi ce module existe

Le modèle baseline (TF-IDF + Régression Logistique) a été entraîné sur le
dataset **GonzaloA/fake_news** (~40 000 articles de presse labellisés).
Problème : les posts Bluesky ne sont **pas** des articles de presse.

Résultat observé sur les 22 184 posts collectés :
- **96,4 % classés « fake »** par le modèle
- Ce chiffre n'est pas crédible : il reflète le biais du modèle face à des
  contenus courts, informels, en français, remplis d'emojis

Exemples de posts classés "fake" à tort :
> « Je suis trop fatigué là 😭 »
> « Quelqu'un a regardé le match hier soir ? »
> « Bonne journée à tous ☀️ »

Ces posts ne contiennent **aucune affirmation factuelle**. Les classer comme
fake news n'a aucun sens.

---

## La solution : pipeline en deux étapes

```
Post Bluesky
     │
     ▼
┌─────────────────────────────────────┐
│  ÉTAPE 1 — Claim Detection           │
│  Ce post contient-il une             │
│  affirmation factuelle vérifiable ?  │
└─────────────────────────────────────┘
     │                  │
    OUI                NON
     │                  │
     ▼                  ▼
Pipeline fake news    Ignoré
(baseline + émotion   (post personnel,
+ score final)         humour, opinion)
```

**Bénéfice attendu :**
- Réduire le nombre de posts analysés à ceux qui le méritent (~50 %)
- Faire passer le taux "fake" de 96,4 % à une valeur plus réaliste (~60-70 %)
- Améliorer la confiance dans les résultats pour la soutenance et la démo

---

## Comment fonctionne le classifieur

Le module `run_claim_filter.py` utilise un **scoring heuristique multi-critères**,
sans appel API externe, bilingue FR/EN. Chaque post reçoit un score entre 0 et 1.

### Score de départ : 0,50 (neutre)

### Les 9 critères

| # | Critère | Effet sur le score | Exemple |
|---|---------|-------------------|---------|
| 1 | **Longueur du texte** | < 8 tokens → −0,30 | Post trop court = probablement personnel |
| 2 | **Pronoms personnels FR** (je, moi, mon, ma, nous…) | Ratio > 15 % → −0,35 | « Je pense que… » |
| 3 | **Pronoms personnels EN** (I, me, my, we, our…) | Ratio > 15 % → −0,35 | « I'm so tired » |
| 4 | **Marqueurs factuels FR** (selon, source, révèle, annonce, étude, enquête, sondage…) | 1 → +0,15 / 2+ → +0,30 | « Selon l'OMS… » |
| 5 | **Marqueurs factuels EN** (according, report, study, found, confirms…) | 1 → +0,15 / 2+ → +0,30 | « According to CNN… » |
| 6 | **Chiffres et statistiques** (%, millions, années YYYY, montants…) | 1 → +0,07 / 2+ → +0,15 | « 40 % des Français… » |
| 7 | **Entités nommées** (séquences de mots avec majuscules = noms propres) | 1 → +0,06 / 2+ → +0,12 | « Emmanuel Macron », « Union Européenne » |
| 8 | **URL** (partage d'un lien = souvent une info) | +0,08 | « https://lemonde.fr/… » |
| 9 | **Emojis excessifs** (≥ 5) ou **hashtags excessifs** (≥ 4) | −0,08 à −0,18 | « 😂😂😂❤️🔥🙏 » |

### Seuil de décision

```
claim_score ≥ 0.50  →  is_claim = True   (affirmation factuelle)
claim_score < 0.50  →  is_claim = False  (post personnel / hors-sujet)
```

Le seuil est configurable via la variable d'environnement `CLAIM_THRESHOLD`.

---

## Exemples concrets

### Posts classés NON-CLAIM (ignorés)

| Post | Score | Raisons |
|------|-------|---------|
| « Je suis trop fatigué là 😭😭😭😭😭 » | 0,02 | personnel_fort, trop_court, emojis_excessifs |
| « Quelqu'un a regardé le match ? » | 0,12 | personnel_fort, trop_court |
| « Bonne journée tout le monde ☀️ » | 0,20 | trop_court, score_neutre |
| « J'adore cette chanson omg 🔥🔥🔥🔥 » | 0,15 | personnel_fort, emojis_excessifs |

### Posts classés CLAIM (analysés)

| Post | Score | Raisons |
|------|-------|---------|
| « Selon l'OMS, 40 % des adultes manquent de vitamine D » | 0,88 | marqueurs_factuels_forts, chiffres_multiples, entites_nommees |
| « Le gouvernement annonce une hausse des impôts de 3 % » | 0,78 | marqueurs_factuel, chiffre, entites_nommees |
| « BREAKING: Le vaccin ARNm cause des myocardites selon une étude » | 0,82 | marqueurs_factuels_forts, entites_nommees |
| « Trump affirme que les élections ont été volées » | 0,75 | marqueur_factuel, entites_nommees |

---

## Résultats attendus

Sur 22 184 posts nettoyés :

| Catégorie | Résultat réel |
|-----------|--------------|
| Affirmations factuelles (is_claim = True) | **19 634 — 88,5 %** |
| Posts personnels filtrés (is_claim = False) | **2 550 — 11,5 %** |
| Temps de traitement | **11,3 secondes** (0 appel API) |

> Pourquoi 88,5 % et non ~50 % ? Parce que les posts ont été collectés avec
> des mots-clés ciblés (fake news, hoax, désinformation, complot…). Les posts
> attirés par ces termes sont naturellement plus "informationnels" que la
> moyenne des posts Bluesky. Les 2 550 filtrés sont des posts qui utilisaient
> ces mots de manière incidente (humour, émotion, post personnel).

---

## Intégration dans le pipeline

### Ordre des étapes (run_all.py)

```
1. collect   →  Collecte Bluesky API
2. clean     →  Nettoyage NLP
2b. claim    →  Filtre Claim Detection  ← NOUVEAU
3. baseline  →  TF-IDF + LogReg scoring
4. emotion   →  VADER + émotions
5. scoring   →  Score final combiné
```

### Données ajoutées dans posts_clean (MongoDB)

Chaque document reçoit 4 nouveaux champs :

```json
{
  "is_claim": true,
  "claim_score": 0.82,
  "claim_reason": "marqueurs_factuels_forts, chiffre, entites_nommees",
  "claim_filtered_at": "2026-06-25T10:00:00Z"
}
```

### Dashboard Streamlit

Un toggle **« Affirmations factuelles uniquement »** a été ajouté dans la sidebar.
Il permet de filtrer instantanément la vue pour ne voir que les posts pertinents,
ce qui rend la démo plus convaincante.

---

## Commandes pour lancer uniquement cette étape

```bash
# Lancer uniquement le claim filter (MongoDB doit être démarré)
python run_all.py --skip-collect --only claim

# Lancer le pipeline complet à partir du claim filter
python run_all.py --skip-collect
```

---

## Limites et pistes d'amélioration

| Limite | Amélioration possible |
|--------|----------------------|
| Heuristique → pas parfaite | Utiliser Groq/Llama pour une classification zero-shot sur les cas ambigus |
| Seuil fixe à 0,50 | Calibrer le seuil sur un jeu de données annoté manuellement |
| Pas de prise en compte du contexte | Intégrer un modèle de détection de claims (ClaimBuster, NLI) |
| Résultats non vérifiés | Annoter 200 posts manuellement pour calculer précision/rappel |

---

*Document généré le 25 juin 2026 — Projet Thumalien M1 Big Data & IA SDV*
