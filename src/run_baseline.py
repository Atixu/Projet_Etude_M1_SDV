"""Partie 3 - Baseline fake news : entrainement, evaluation et scoring.

Strategie:
1. Charge un dataset public labellise fake/real (HuggingFace: GonzaloA/fake_news).
2. Entraine TF-IDF (unigrams+bigrams) + Logistic Regression.
3. Evalue sur split test : F1, precision, rappel, matrice de confusion.
4. Applique le modele sur nos 4618 posts Bluesky pour produire un score de credibilite.
5. Ecrit les scores dans MongoDB (champ credibility_score sur posts_clean).
6. Sauvegarde le modele dans models/.

Variables d'environnement:
- MONGO_URI (requis)
- MONGO_DB, MONGO_COLLECTION_CLEAN (optionnels)
- DOTENV_PATH (optionnel)
- BASELINE_MODEL_DIR (defaut: models/)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from datetime import datetime, timezone

import joblib
import numpy as np
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from codecarbon import EmissionsTracker

PIPELINE_VERSION = "baseline_tfidf_logreg_v1"


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


# ---------------------------------------------------------------------------
# 1. Chargement du dataset d'entrainement
# ---------------------------------------------------------------------------

def load_training_data() -> tuple[list[str], list[int]]:
    """Charge le dataset GonzaloA/fake_news depuis HuggingFace.

    Labels: 0 = fake, 1 = real.
    Retourne (texts, labels).
    """
    logging.info("Loading training dataset from HuggingFace...")
    ds = load_dataset("GonzaloA/fake_news", trust_remote_code=True)

    texts, labels = [], []
    for split in ("train", "test", "validation"):
        if split not in ds:
            continue
        for row in ds[split]:
            text = (row.get("text") or "") + " " + (row.get("title") or "")
            text = text.strip()
            label = int(row.get("label", -1))
            if text and label in (0, 1):
                texts.append(text)
                labels.append(label)

    logging.info("Training data loaded: %s samples (fake=%s real=%s)",
                 len(texts), labels.count(0), labels.count(1))
    return texts, labels


# ---------------------------------------------------------------------------
# 2. Entrainement
# ---------------------------------------------------------------------------

def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=50_000,
            sublinear_tf=True,
            min_df=2,
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            C=1.0,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])


def train_and_evaluate(
    texts: list[str],
    labels: list[int],
    model_dir: Path,
) -> Pipeline:
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    logging.info("Training: train=%s test=%s", len(X_train), len(X_test))

    pipe = build_pipeline()
    model_dir.mkdir(parents=True, exist_ok=True)
    with EmissionsTracker(
        output_dir=str(model_dir),
        project_name="baseline_training",
        log_level="error",
    ) as tracker:
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
    emissions_kg = tracker.final_emissions
    logging.info("Training CO2 emissions: %.6f kgCO2eq", emissions_kg)

    f1 = f1_score(y_test, y_pred, average="weighted")

    logging.info("=== Evaluation baseline ===")
    logging.info("F1 weighted: %.4f", f1)
    report = classification_report(
        y_test, y_pred,
        target_names=["fake", "real"],
        digits=4,
    )
    for line in report.splitlines():
        logging.info(line)

    cm = confusion_matrix(y_test, y_pred)
    logging.info("Confusion matrix (fake/real):\n%s", cm)

    # Sauvegarde modele
    model_path = model_dir / "baseline_tfidf_logreg.joblib"
    joblib.dump(pipe, model_path)
    logging.info("Model saved: %s", model_path)

    # Sauvegarde rapport texte
    report_path = model_dir / "evaluation_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Pipeline: {PIPELINE_VERSION}\n")
        f.write(f"Date: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Train size: {len(X_train)} | Test size: {len(X_test)}\n")
        f.write(f"F1 weighted: {f1:.4f}\n")
        f.write(f"CO2 emissions (training): {emissions_kg:.6f} kgCO2eq\n\n")
        f.write(report)
        f.write(f"\nConfusion matrix:\n{cm}\n")
    logging.info("Evaluation report saved: %s", report_path)

    return pipe


# ---------------------------------------------------------------------------
# 3. Scoring des posts Bluesky
# ---------------------------------------------------------------------------

def score_bluesky_posts(
    pipe: Pipeline,
    mongo_uri: str,
    db_name: str,
    clean_col_name: str,
) -> None:
    client = MongoClient(mongo_uri)
    col = client[db_name][clean_col_name]

    total = col.count_documents({})
    logging.info("Scoring %s Bluesky posts...", total)

    docs = list(col.find({}, {"uri": 1, "clean_text": 1, "lang": 1}))

    texts = [d.get("clean_text") or "" for d in docs]

    # Probabilites : index 0 = fake, index 1 = real
    probas = pipe.predict_proba(texts)
    predictions = pipe.predict(texts)

    scored_at = datetime.now(timezone.utc).isoformat()
    ops: list[UpdateOne] = []

    for doc, proba, pred in zip(docs, probas, predictions):
        uri = doc.get("uri")
        if not uri:
            continue

        prob_fake = float(proba[0])
        prob_real = float(proba[1])
        # Score de credibilite : 0 = tres douteux, 1 = tres fiable
        credibility_score = round(prob_real, 4)

        # Niveau d'alerte
        if credibility_score < 0.35:
            alert_level = "high"
        elif credibility_score < 0.60:
            alert_level = "medium"
        else:
            alert_level = "low"

        ops.append(UpdateOne(
            {"uri": uri},
            {"$set": {
                "credibility_score": credibility_score,
                "prob_fake": round(prob_fake, 4),
                "prob_real": round(prob_real, 4),
                "predicted_label": "fake" if pred == 0 else "real",
                "alert_level": alert_level,
                "scored_at": scored_at,
                "scoring_pipeline": PIPELINE_VERSION,
            }},
        ))

        if len(ops) >= 500:
            _bulk(col, ops)
            ops = []

    if ops:
        _bulk(col, ops)

    # Stats finales
    fake_count = col.count_documents({"predicted_label": "fake"})
    real_count = col.count_documents({"predicted_label": "real"})
    high_alert = col.count_documents({"alert_level": "high"})
    logging.info(
        "Scoring done: fake=%s real=%s high_alert=%s",
        fake_count, real_count, high_alert,
    )


def _bulk(col, ops: list) -> None:
    try:
        col.bulk_write(ops, ordered=False)
    except BulkWriteError as exc:
        logging.warning("Bulk write warning: %s", exc.details)


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main() -> None:
    _setup_logging()
    _load_environment()

    mongo_uri = _required_env("MONGO_URI")
    db_name = os.getenv("MONGO_DB", "bluesky")
    clean_col_name = os.getenv("MONGO_COLLECTION_CLEAN", "posts_clean")
    model_dir = Path(os.getenv("BASELINE_MODEL_DIR", "models"))

    # Entrainement (Partie 7 - mesure energetique)
    texts, labels = load_training_data()
    with track_energy("baseline_training", n_samples=len(texts)):
        pipe = train_and_evaluate(texts, labels, model_dir)

    # Scoring des posts Bluesky (Partie 7 - mesure energetique inference)
    with track_energy("baseline_inference"):
        score_bluesky_posts(pipe, mongo_uri, db_name, clean_col_name)


if __name__ == "__main__":
    main()
