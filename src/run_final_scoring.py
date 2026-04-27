"""Partie 5 - Score de credibilite final et explicabilite.

Combine les signaux existants:
- credibilite baseline fake news (Partie 3)
- sentiment (Partie 4)
- emotions (Partie 4)

Sortie ajoutee dans posts_clean:
- final_credibility_score
- final_risk_score
- final_alert_level
- score_breakdown
- explanation_text
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

FINAL_SCORING_VERSION = "final_scoring_v1"


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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _emotion_risk(emotions: dict) -> float:
    anger = float(emotions.get("anger", 0.0))
    fear = float(emotions.get("fear", 0.0))
    sadness = float(emotions.get("sadness", 0.0))
    joy = float(emotions.get("joy", 0.0))
    humor = float(emotions.get("humor", 0.0))
    surprise = float(emotions.get("surprise", 0.0))

    # Les emotions negatives augmentent le risque; positives le reduisent.
    raw = (
        (1.2 * anger)
        + (1.0 * fear)
        + (0.8 * sadness)
        - (0.6 * joy)
        - (0.3 * humor)
        - (0.1 * surprise)
    )
    return _clamp(raw)


def _alert_level(score: float) -> str:
    if score < 0.35:
        return "high"
    if score < 0.60:
        return "medium"
    return "low"


def _build_explanation(
    base_credibility: float,
    sentiment_compound: float,
    emotion_risk: float,
    dominant_emotion: str,
    final_score: float,
) -> str:
    parts: list[str] = []

    if base_credibility < 0.35:
        parts.append("Le modele fake-news de base estime une faible credibilite.")
    elif base_credibility < 0.60:
        parts.append("Le modele fake-news de base indique une credibilite moyenne.")
    else:
        parts.append("Le modele fake-news de base indique une credibilite plutot elevee.")

    if sentiment_compound <= -0.30:
        parts.append("Le ton global est negatif, ce qui augmente le risque de contenu trompeur.")
    elif sentiment_compound >= 0.30:
        parts.append("Le ton global est plutot positif, ce qui reduit legerement le risque.")

    if emotion_risk >= 0.10:
        parts.append(
            f"Des emotions a risque sont detectees (emotion dominante: {dominant_emotion})."
        )
    elif dominant_emotion and dominant_emotion != "neutral":
        parts.append(f"Emotion dominante detectee: {dominant_emotion}.")

    level = _alert_level(final_score)
    parts.append(f"Niveau d'alerte final: {level}.")

    return " ".join(parts)


def _bulk(col, ops: list[UpdateOne]) -> None:
    if not ops:
        return
    try:
        col.bulk_write(ops, ordered=False)
    except BulkWriteError as exc:
        logging.warning("Bulk write warning: %s", exc.details)


def main() -> None:
    _setup_logging()
    _load_environment()

    mongo_uri = _required_env("MONGO_URI")
    db_name = os.getenv("MONGO_DB", "bluesky")
    clean_col_name = os.getenv("MONGO_COLLECTION_CLEAN", "posts_clean")
    batch_size = int(os.getenv("FINAL_SCORING_BATCH_SIZE", "500"))

    # Poids configurables.
    w_fake = float(os.getenv("WEIGHT_FAKE_RISK", "0.70"))
    w_sent = float(os.getenv("WEIGHT_SENTIMENT_RISK", "0.20"))
    w_emo = float(os.getenv("WEIGHT_EMOTION_RISK", "0.10"))

    total_w = w_fake + w_sent + w_emo
    if total_w <= 0:
        raise RuntimeError("Invalid weights: sum must be > 0")

    # Normalisation defensive des poids.
    w_fake /= total_w
    w_sent /= total_w
    w_emo /= total_w

    client = MongoClient(mongo_uri)
    col = client[db_name][clean_col_name]

    total = col.count_documents({})
    logging.info(
        "Start final scoring: docs=%s weights(fake=%.2f sent=%.2f emo=%.2f)",
        total,
        w_fake,
        w_sent,
        w_emo,
    )

    cursor = col.find(
        {},
        {
            "uri": 1,
            "credibility_score": 1,
            "sentiment_compound": 1,
            "dominant_emotion": 1,
            "emotion_scores": 1,
        },
    )

    scored_at = datetime.now(timezone.utc).isoformat()
    ops: list[UpdateOne] = []
    processed = 0

    for doc in cursor:
        processed += 1
        uri = doc.get("uri")
        if not uri:
            continue

        base_credibility = float(doc.get("credibility_score", 0.5))
        fake_risk = _clamp(1.0 - base_credibility)

        sentiment_compound = float(doc.get("sentiment_compound", 0.0))
        sentiment_risk = _clamp(max(0.0, -sentiment_compound))

        emotions = doc.get("emotion_scores") or {}
        emo_risk = _emotion_risk(emotions)
        dom_emo = doc.get("dominant_emotion", "neutral")

        final_risk = _clamp(
            (w_fake * fake_risk) + (w_sent * sentiment_risk) + (w_emo * emo_risk)
        )
        final_score = round(_clamp(1.0 - final_risk), 4)
        final_level = _alert_level(final_score)

        explanation_text = _build_explanation(
            base_credibility=base_credibility,
            sentiment_compound=sentiment_compound,
            emotion_risk=emo_risk,
            dominant_emotion=dom_emo,
            final_score=final_score,
        )

        ops.append(
            UpdateOne(
                {"uri": uri},
                {
                    "$set": {
                        "final_credibility_score": final_score,
                        "final_risk_score": round(final_risk, 4),
                        "final_alert_level": final_level,
                        "score_breakdown": {
                            "base_credibility": round(base_credibility, 4),
                            "fake_risk": round(fake_risk, 4),
                            "sentiment_compound": round(sentiment_compound, 4),
                            "sentiment_risk": round(sentiment_risk, 4),
                            "emotion_risk": round(emo_risk, 4),
                            "weights": {
                                "fake_risk": round(w_fake, 4),
                                "sentiment_risk": round(w_sent, 4),
                                "emotion_risk": round(w_emo, 4),
                            },
                        },
                        "explanation_text": explanation_text,
                        "final_scored_at": scored_at,
                        "final_scoring_pipeline": FINAL_SCORING_VERSION,
                    }
                },
            )
        )

        if len(ops) >= batch_size:
            _bulk(col, ops)
            ops = []
            logging.info("Progress final scoring: %s/%s", processed, total)

    if ops:
        _bulk(col, ops)

    low = col.count_documents({"final_alert_level": "low"})
    medium = col.count_documents({"final_alert_level": "medium"})
    high = col.count_documents({"final_alert_level": "high"})

    logging.info(
        "Final scoring done: low=%s medium=%s high=%s",
        low,
        medium,
        high,
    )


if __name__ == "__main__":
    main()
