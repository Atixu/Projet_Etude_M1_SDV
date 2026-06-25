"""Nodes du pipeline NLP Cleaning.

Chaque node est une fonction pure qui prend des données en entrée
et retourne des données transformées. Kedro orchestre la chaîne.

Étapes :
1. extract_raw_posts   — Lecture MongoDB posts_raw → DataFrame
2. clean_text_node     — Suppression URLs, mentions, hashtags
3. detect_language_node — Détection langue réelle (langdetect), filtre anglais
4. normalize_text_node — Minuscules, suppression accents, filtrage ASCII
5. tokenize_text_node  — Découpage en tokens (NLTK ou split)
6. lemmatize_text_node — Réduction à la forme canonique (NLTK WordNetLemmatizer)
7. load_clean_posts    — Écriture MongoDB posts_clean_kedro
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone

import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex réutilisés dans plusieurs nodes
# ---------------------------------------------------------------------------
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"@[\w.:-]+")
HASHTAG_RE = re.compile(r"#\w+")
MULTISPACE_RE = re.compile(r"\s+")
NONASCII_RE = re.compile(r"[^a-z0-9\s]")


def _strip_accents(text: str) -> str:
    """Supprime les accents d'une chaîne Unicode."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


# ---------------------------------------------------------------------------
# Node 1 — Extraction MongoDB
# ---------------------------------------------------------------------------
def extract_raw_posts(
    mongo_uri: str,
    database: str,
    raw_collection: str,
) -> pd.DataFrame:
    """Lit les posts bruts depuis MongoDB et retourne un DataFrame.

    Args:
        mongo_uri: URI de connexion MongoDB.
        database: Nom de la base de données.
        raw_collection: Nom de la collection source (posts_raw).

    Returns:
        DataFrame avec colonnes : uri, text, langs, created_at, author_did.
    """
    from pymongo import MongoClient

    client = MongoClient(mongo_uri)
    col = client[database][raw_collection]

    projection = {"_id": 0, "uri": 1, "post": 1}
    docs = list(col.find({}, projection))

    if not docs:
        log.warning("Aucun document trouvé dans %s.%s", database, raw_collection)
        return pd.DataFrame(columns=["uri", "text", "langs", "created_at", "author_did"])

    rows = []
    for doc in docs:
        post = doc.get("post", {})
        record = post.get("record", {})
        text = record.get("text", "").strip()
        if not text:
            continue
        rows.append({
            "uri": doc.get("uri", ""),
            "text": text,
            "langs": record.get("langs") or [],
            "created_at": record.get("createdAt", ""),
            "author_did": post.get("author", {}).get("did", ""),
        })

    df = pd.DataFrame(rows)
    log.info("Node extract: %d posts extraits depuis %s.%s", len(df), database, raw_collection)
    return df


# ---------------------------------------------------------------------------
# Node 2 — Nettoyage (cleaning)
# ---------------------------------------------------------------------------
def clean_text_node(raw_posts: pd.DataFrame) -> pd.DataFrame:
    """Supprime URLs, mentions (@user) et hashtags (#mot) du texte.

    Input  : raw_posts (uri, text, langs, created_at, author_did)
    Output : même DataFrame + colonne text_cleaned
    """
    def _clean(text: str) -> str:
        if not isinstance(text, str):
            return ""
        t = URL_RE.sub(" ", text)
        t = MENTION_RE.sub(" ", t)
        t = HASHTAG_RE.sub(" ", t)
        return MULTISPACE_RE.sub(" ", t).strip()

    df = raw_posts.copy()
    df["text_cleaned"] = df["text"].apply(_clean)
    before = len(df)
    df = df[df["text_cleaned"].str.len() > 0].reset_index(drop=True)
    log.info(
        "Node clean: %d/%d posts apres suppression URLs/mentions/hashtags",
        len(df), before,
    )
    return df


# ---------------------------------------------------------------------------
# Node 3 — Détection de langue
# ---------------------------------------------------------------------------
def detect_language_node(
    cleaned_posts: pd.DataFrame,
    target_lang: str,
) -> pd.DataFrame:
    """Détecte la langue réelle du texte et filtre pour ne garder que target_lang.

    On utilise langdetect (analyse du contenu) et non le tag déclaré par l'auteur,
    qui est souvent incorrect (ex. Allemand déclarant 'en').

    Input  : cleaned_posts
    Output : DataFrame filtré avec colonne detected_lang
    """
    from langdetect import LangDetectException, detect

    def _detect(text: str) -> str:
        try:
            return detect(text)
        except LangDetectException:
            return "unknown"

    df = cleaned_posts.copy()
    df["detected_lang"] = df["text_cleaned"].apply(_detect)
    before = len(df)
    df = df[df["detected_lang"] == target_lang].reset_index(drop=True)
    log.info(
        "Node detect_lang: %d/%d posts retenus (langue=%s)",
        len(df), before, target_lang,
    )
    return df


# ---------------------------------------------------------------------------
# Node 4 — Normalisation
# ---------------------------------------------------------------------------
def normalize_text_node(lang_filtered: pd.DataFrame) -> pd.DataFrame:
    """Normalise le texte : minuscules, suppression accents, filtrage ASCII.

    Input  : lang_filtered
    Output : DataFrame + colonne text_normalized
    """
    def _normalize(text: str) -> str:
        t = text.lower()
        t = _strip_accents(t)
        t = NONASCII_RE.sub(" ", t)
        return MULTISPACE_RE.sub(" ", t).strip()

    df = lang_filtered.copy()
    df["text_normalized"] = df["text_cleaned"].apply(_normalize)
    before = len(df)
    df = df[df["text_normalized"].str.len() > 0].reset_index(drop=True)
    log.info("Node normalize: %d/%d posts apres normalisation", len(df), before)
    return df


# ---------------------------------------------------------------------------
# Node 5 — Tokenisation
# ---------------------------------------------------------------------------
def tokenize_text_node(
    normalized_posts: pd.DataFrame,
    min_token_count: int,
) -> pd.DataFrame:
    """Découpe le texte normalisé en liste de tokens (mots).

    Utilise NLTK word_tokenize si disponible, sinon str.split().

    Input  : normalized_posts
    Output : DataFrame + colonnes tokens, token_count
    """
    try:
        import nltk
        from nltk.tokenize import word_tokenize
        nltk.download("punkt_tab", quiet=True)

        def _tokenize(text: str) -> list[str]:
            return word_tokenize(text) if text else []

        log.info("Tokenisation avec NLTK word_tokenize")
    except ImportError:
        def _tokenize(text: str) -> list[str]:  # type: ignore[misc]
            return text.split() if text else []

        log.info("Tokenisation avec str.split (NLTK non disponible)")

    df = normalized_posts.copy()
    df["tokens"] = df["text_normalized"].apply(_tokenize)
    df["token_count"] = df["tokens"].apply(len)
    before = len(df)
    df = df[df["token_count"] >= min_token_count].reset_index(drop=True)
    log.info(
        "Node tokenize: %d/%d posts (min %d tokens)",
        len(df), before, min_token_count,
    )
    return df


# ---------------------------------------------------------------------------
# Node 6 — Lemmatisation
# ---------------------------------------------------------------------------
def lemmatize_text_node(
    tokenized_posts: pd.DataFrame,
    use_nltk_lemmatizer: bool,
) -> pd.DataFrame:
    """Réduit chaque token à sa forme canonique (lemme).

    Exemple : 'running' → 'run', 'politicians' → 'politician'.
    Produit aussi clean_text (tokens rejoints) pour le modèle ML.

    Input  : tokenized_posts
    Output : DataFrame + colonnes lemmatized_tokens, clean_text
    """
    if use_nltk_lemmatizer:
        try:
            import nltk
            from nltk.stem import WordNetLemmatizer
            nltk.download("wordnet", quiet=True)
            lemmatizer = WordNetLemmatizer()

            def _lemmatize(tokens: list) -> list[str]:
                return [lemmatizer.lemmatize(t) for t in tokens]

            log.info("Lemmatisation avec NLTK WordNetLemmatizer")
        except ImportError:
            def _lemmatize(tokens: list) -> list[str]:  # type: ignore[misc]
                return list(tokens)

            log.warning("NLTK non disponible — lemmatisation desactivee")
    else:
        def _lemmatize(tokens: list) -> list[str]:  # type: ignore[misc]
            return list(tokens)

    df = tokenized_posts.copy()
    df["lemmatized_tokens"] = df["tokens"].apply(_lemmatize)
    df["clean_text"] = df["lemmatized_tokens"].apply(lambda t: " ".join(t))
    log.info("Node lemmatize: %d posts traites", len(df))
    return df


# ---------------------------------------------------------------------------
# Node 7 — Chargement dans MongoDB
# ---------------------------------------------------------------------------
def load_clean_posts(
    lemmatized_posts: pd.DataFrame,
    mongo_uri: str,
    database: str,
    clean_collection: str,
) -> pd.DataFrame:
    """Écrit les posts nettoyés dans MongoDB (upsert sur uri).

    Input  : lemmatized_posts (DataFrame complet après lemmatisation)
    Output : DataFrame de résumé (1 ligne) avec statistiques de chargement
    """
    from pymongo import MongoClient, UpdateOne

    client = MongoClient(mongo_uri)
    col = client[database][clean_collection]
    cleaned_at = datetime.now(timezone.utc).isoformat()

    ops = []
    for _, row in lemmatized_posts.iterrows():
        # Parquet recharge les listes Python en numpy arrays — MongoDB ne les encode pas
        tokens = row.get("tokens", [])
        if hasattr(tokens, "tolist"):
            tokens = tokens.tolist()
        lemmatized = row.get("lemmatized_tokens", [])
        if hasattr(lemmatized, "tolist"):
            lemmatized = lemmatized.tolist()

        doc = {
            "uri": row["uri"],
            "text": row.get("text", ""),
            "clean_text": row.get("clean_text", ""),
            "detected_lang": row.get("detected_lang", "en"),
            "tokens": tokens,
            "lemmatized_tokens": lemmatized,
            "token_count": int(row.get("token_count", 0)),
            "created_at": row.get("created_at", ""),
            "author_did": row.get("author_did", ""),
            "pipeline": "kedro_nlp_cleaning_v1",
            "cleaned_at": cleaned_at,
        }
        ops.append(UpdateOne({"uri": row["uri"]}, {"$set": doc}, upsert=True))

    upserted, modified = 0, 0
    if ops:
        result = col.bulk_write(ops)
        upserted = result.upserted_count
        modified = result.modified_count

    log.info(
        "Node load: %d docs chargés dans %s.%s (upserted=%d modified=%d)",
        len(lemmatized_posts), database, clean_collection, upserted, modified,
    )

    return pd.DataFrame([{
        "total_posts": len(lemmatized_posts),
        "upserted": upserted,
        "modified": modified,
        "collection": clean_collection,
        "loaded_at": cleaned_at,
    }])
