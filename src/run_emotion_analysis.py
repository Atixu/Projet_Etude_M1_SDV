"""Partie 4 - Analyse emotionnelle sur posts_clean.

Adds on each post:
- sentiment_compound, sentiment_label (VADER)
- emotion_scores (anger/fear/sadness/joy/surprise/humor)
- dominant_emotion
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from emotion_analysis import dominant_emotion, emotion_scores
from energy_monitoring import track_energy

EMOTION_PIPELINE_VERSION = "emotion_baseline_v1"


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
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def sentiment_label(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


def _bulk(col, ops: list[UpdateOne]) -> None:
    if not ops:
        return
    try:
        col.bulk_write(ops, ordered=False)
    except BulkWriteError as exc:
        logging.warning("Bulk write warning: %s", exc.details)


def analyze_emotions(col, total: int, batch_size: int) -> None:
    """Boucle d'inference emotionnelle (VADER + lexique) sur tous les posts."""
    analyzer = SentimentIntensityAnalyzer()
    scored_at = datetime.now(timezone.utc).isoformat()

    cursor = col.find({}, {"uri": 1, "clean_text": 1, "text": 1})

    ops: list[UpdateOne] = []
    processed = 0

    for doc in cursor:
        processed += 1
        uri = doc.get("uri")
        if not uri:
            continue

        text = (doc.get("clean_text") or doc.get("text") or "").strip()
        if not text:
            continue

        s = analyzer.polarity_scores(text)
        e_scores = emotion_scores(text)
        dom = dominant_emotion(e_scores)

        ops.append(
            UpdateOne(
                {"uri": uri},
                {
                    "$set": {
                        "emotion_scores": e_scores,
                        "dominant_emotion": dom,
                        "sentiment_compound": round(float(s["compound"]), 4),
                        "sentiment_pos": round(float(s["pos"]), 4),
                        "sentiment_neu": round(float(s["neu"]), 4),
                        "sentiment_neg": round(float(s["neg"]), 4),
                        "sentiment_label": sentiment_label(float(s["compound"])),
                        "emotion_scored_at": scored_at,
                        "emotion_pipeline": EMOTION_PIPELINE_VERSION,
                    }
                },
            )
        )

        if len(ops) >= batch_size:
            _bulk(col, ops)
            ops = []
            logging.info("Progress emotion: %s/%s", processed, total)

    if ops:
        _bulk(col, ops)


def main() -> None:
    _setup_logging()
    _load_environment()

    mongo_uri = _required_env("MONGO_URI")
    db_name = os.getenv("MONGO_DB", "bluesky")
    clean_col_name = os.getenv("MONGO_COLLECTION_CLEAN", "posts_clean")
    batch_size = int(os.getenv("EMOTION_BATCH_SIZE", "500"))

    client = MongoClient(mongo_uri)
    col = client[db_name][clean_col_name]

    total = col.count_documents({})
    logging.info("Start emotion analysis: docs=%s batch_size=%s", total, batch_size)

    # Partie 7 - mesure energetique de l'inference emotionnelle
    with track_energy("emotion_inference", n_samples=total):
        analyze_emotions(col, total, batch_size)

    high_neg = col.count_documents({"sentiment_label": "negative"})
    pos = col.count_documents({"sentiment_label": "positive"})
    neu = col.count_documents({"sentiment_label": "neutral"})

    logging.info(
        "Emotion analysis done: positive=%s neutral=%s negative=%s",
        pos,
        neu,
        high_neg,
    )


if __name__ == "__main__":
    main()
