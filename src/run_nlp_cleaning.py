"""Pipeline de nettoyage NLP : posts_raw -> posts_clean.

Lit tous les documents de posts_raw, applique le nettoyage de texte
language-aware, enrichit avec des metadonnees d'engagement, et ecrit
dans posts_clean (upsert idempotent sur uri).

Variables d'environnement:
- MONGO_URI (requis)
- MONGO_DB          (defaut: bluesky)
- MONGO_COLLECTION_RAW   (defaut: posts_raw)
- MONGO_COLLECTION_CLEAN (defaut: posts_clean)
- NLP_BATCH_SIZE    (defaut: 500)
- DOTENV_PATH       (chemin .env optionnel)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

# Le module nlp_cleaning est dans le meme dossier src/.
from nlp_cleaning import clean_text, extract_lang, token_count

PIPELINE_VERSION = "nlp_cleaning_v2"


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def _load_environment() -> None:
    dotenv_path = os.getenv("DOTENV_PATH")
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path)
        return
    project_root_env = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=project_root_env)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _build_clean_doc(raw_doc: dict[str, Any], cleaned_at: str) -> dict[str, Any] | None:
    """Transforme un document brut en document clean. Retourne None si texte vide."""
    post = raw_doc.get("post", {})
    record = post.get("record", {})
    author = post.get("author", {})
    feed_ctx = raw_doc.get("feed_context", {})

    uri = raw_doc.get("uri") or post.get("uri")
    if not uri:
        return None

    text = record.get("text", "") or ""
    langs = record.get("langs") or []
    lang = extract_lang(langs)

    cleaned = clean_text(text, lang=lang)
    tokens = token_count(cleaned)

    return {
        "uri": uri,
        # Texte
        "text": text,
        "clean_text": cleaned,
        "token_count": tokens,
        # Langue
        "lang": lang,
        "langs_raw": langs,
        # Auteur
        "author_handle": author.get("handle"),
        "author_did": author.get("did"),
        "author_display_name": author.get("displayName"),
        # Metadonnees temporelles
        "created_at": record.get("createdAt"),
        "cleaned_at": cleaned_at,
        # Engagement
        "like_count": post.get("likeCount", 0),
        "reply_count": post.get("replyCount", 0),
        "repost_count": post.get("repostCount", 0),
        "bookmark_count": post.get("bookmarkCount", 0),
        # Contexte de collecte
        "search_term": feed_ctx.get("search_term"),
        "collected_at": feed_ctx.get("collected_at"),
        # Pipeline
        "pipeline": PIPELINE_VERSION,
    }


def process_batch(
    ops_buffer: list[UpdateOne],
    clean_col: Any,
) -> dict[str, int]:
    if not ops_buffer:
        return {"upserted": 0, "matched": 0, "modified": 0}
    try:
        res = clean_col.bulk_write(ops_buffer, ordered=False)
        return {
            "upserted": res.upserted_count,
            "matched": res.matched_count,
            "modified": res.modified_count,
        }
    except BulkWriteError as exc:
        logging.warning("Bulk write partial error: %s", exc.details)
        return {"upserted": 0, "matched": 0, "modified": 0}


def main() -> None:
    _setup_logging()
    _load_environment()

    mongo_uri = _required_env("MONGO_URI")
    db_name = os.getenv("MONGO_DB", "bluesky")
    raw_col_name = os.getenv("MONGO_COLLECTION_RAW", "posts_raw")
    clean_col_name = os.getenv("MONGO_COLLECTION_CLEAN", "posts_clean")
    batch_size = int(os.getenv("NLP_BATCH_SIZE", "500"))

    client = MongoClient(mongo_uri)
    db = client[db_name]
    raw_col = db[raw_col_name]
    clean_col = db[clean_col_name]

    # Index unique pour idempotence.
    clean_col.create_index("uri", unique=True)

    total_raw = raw_col.count_documents({})
    logging.info(
        "Start NLP cleaning: raw_docs=%s batch_size=%s -> %s",
        total_raw, batch_size, clean_col_name,
    )

    cleaned_at = datetime.now(timezone.utc).isoformat()
    ops: list[UpdateOne] = []
    total_upserted = total_matched = total_skipped = 0
    processed = 0

    cursor = raw_col.find({}, no_cursor_timeout=False)

    for raw_doc in cursor:
        clean_doc = _build_clean_doc(raw_doc, cleaned_at)
        processed += 1

        if clean_doc is None or not clean_doc["clean_text"]:
            total_skipped += 1
            continue

        ops.append(
            UpdateOne({"uri": clean_doc["uri"]}, {"$set": clean_doc}, upsert=True)
        )

        if len(ops) >= batch_size:
            stats = process_batch(ops, clean_col)
            total_upserted += stats["upserted"]
            total_matched += stats["matched"]
            ops = []
            logging.info("Progress: processed=%s upserted=%s", processed, total_upserted)

    # Dernier batch.
    if ops:
        stats = process_batch(ops, clean_col)
        total_upserted += stats["upserted"]
        total_matched += stats["matched"]

    total_clean = clean_col.count_documents({})
    logging.info(
        "NLP cleaning done: raw=%s processed=%s skipped=%s upserted=%s matched=%s clean_total=%s",
        total_raw, processed, total_skipped, total_upserted, total_matched, total_clean,
    )


if __name__ == "__main__":
    main()
