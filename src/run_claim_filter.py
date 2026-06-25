"""Partie 2b - Filtre d'affirmations factuelles (claim detection).

Distingue les posts qui contiennent une affirmation factuelle verifiable
(fausse info potentielle, actu, statistique...) des posts personnels
(vie quotidienne, humour, opinion pure).

Approche : scoring heuristique multi-criteres, bilingue FR/EN.
Sortie ajoutee dans posts_clean :
- is_claim        (bool)  : True = affirmation factuelle detectee
- claim_score     (float) : 0.0 (tres personnel) a 1.0 (tres factuel)
- claim_reason    (str)   : raisons principales de la decision

Variables d'environnement :
- MONGO_URI               (requis)
- MONGO_DB                (defaut : bluesky)
- MONGO_COLLECTION_CLEAN  (defaut : posts_clean)
- CLAIM_THRESHOLD         (defaut : 0.5)
- CLAIM_BATCH_SIZE        (defaut : 500)
- DOTENV_PATH             (optionnel)
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

CLAIM_FILTER_VERSION = "claim_filter_v1"

# ── Regex compilees une seule fois ───────────────────────────────────────────

_PERSONAL_FR = re.compile(
    r"\b(je|j'|jme|moi|mon|ma|mes|notre|nos|nous|me|m'|tu|ton|ta|tes|vous|votre)\b",
    re.IGNORECASE,
)
_PERSONAL_EN = re.compile(
    r"\b(i'm|i've|i'll|i'd|i am|i have|\bi\b|me|my|myself|we|our|ourselves|you|your)\b",
    re.IGNORECASE,
)
_FACTUAL_FR = re.compile(
    r"\b(selon|d'apres|d'après|source|revele|révèle|annonce|affirme|declare|déclare|"
    r"confirme|rapporte|montre|prouve|indique|etude|étude|rapport|enquete|enquête|"
    r"sondage|chiffres?|statistiques?|recherche|scientifique|officiel|gouvernement|"
    r"ministre|president|tribunal|justice|loi|vote|election|élection|vaccin|"
    r"complot|propagande|fake|intox|hoax|desinformation|désinformation)\b",
    re.IGNORECASE,
)
_FACTUAL_EN = re.compile(
    r"\b(according|sources?|reveals?|announces?|claims?|confirms?|reports?|shows?|"
    r"proves?|indicates?|study|studies|report|survey|research|found|says|said|"
    r"scientists?|officials?|government|minister|president|court|law|vote|election|"
    r"vaccine|conspiracy|propaganda|fake|misinformation|disinformation|hoax)\b",
    re.IGNORECASE,
)
_NUMBERS = re.compile(
    r"\b\d+[\d\s,.]*(?:%|millions?|milliards?|billions?|k\b|euros?|dollars?|\$|€)"
    r"|\b\d{4}\b"
)
_NAMED_ENTITIES = re.compile(
    r"(?<![.!?]\s)(?<!\n)([A-ZÀ-Ÿ][a-zà-ÿ]{2,}(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]{2,})+)"
)
_EMOJIS = re.compile("[\U00010000-\U0010ffff]", flags=re.UNICODE)
_URL = re.compile(r"https?://\S+")
_HASHTAGS = re.compile(r"#\w+")


# ── Classifieur heuristique ───────────────────────────────────────────────────

def classify_claim(text: str, clean_text: str) -> tuple[bool, float, str]:
    """Retourne (is_claim, claim_score, claim_reason).

    Score de 0.0 (post personnel) a 1.0 (affirmation factuelle certaine).
    Seuil par defaut : 0.5.
    """
    score = 0.50
    reasons: list[str] = []
    words = text.split()
    word_count = max(len(words), 1)

    # ── 1. Longueur ──────────────────────────────────────────────────────────
    token_count = len(clean_text.split())
    if token_count < 8:
        score -= 0.30
        reasons.append("trop_court")
    elif token_count >= 25:
        score += 0.08

    # ── 2. Pronoms personnels (indicateur fort de post perso) ────────────────
    personal_count = len(_PERSONAL_FR.findall(text)) + len(_PERSONAL_EN.findall(text))
    personal_ratio = personal_count / word_count
    if personal_ratio >= 0.15:
        score -= 0.35
        reasons.append("personnel_fort")
    elif personal_ratio >= 0.08:
        score -= 0.18
        reasons.append("personnel_modere")

    # ── 3. Marqueurs factuels FR + EN ────────────────────────────────────────
    factual_count = len(_FACTUAL_FR.findall(text)) + len(_FACTUAL_EN.findall(text))
    if factual_count >= 2:
        score += 0.30
        reasons.append("marqueurs_factuels_forts")
    elif factual_count == 1:
        score += 0.15
        reasons.append("marqueur_factuel")

    # ── 4. Chiffres et statistiques ──────────────────────────────────────────
    num_matches = _NUMBERS.findall(text)
    if len(num_matches) >= 2:
        score += 0.15
        reasons.append("chiffres_multiples")
    elif len(num_matches) == 1:
        score += 0.07
        reasons.append("chiffre")

    # ── 5. Entites nommees (noms propres en sequence) ────────────────────────
    entities = _NAMED_ENTITIES.findall(text)
    if len(entities) >= 2:
        score += 0.12
        reasons.append("entites_nommees")
    elif len(entities) == 1:
        score += 0.06

    # ── 6. URLs (partage d'info externe) ─────────────────────────────────────
    if _URL.search(text):
        score += 0.08
        reasons.append("url")

    # ── 7. Hashtags (usage social -> plus personnel) ──────────────────────────
    hashtag_count = len(_HASHTAGS.findall(text))
    if hashtag_count >= 4:
        score -= 0.12
        reasons.append("hashtags_excessifs")

    # ── 8. Emojis excessifs (post emotionnel/perso) ───────────────────────────
    emoji_count = len(_EMOJIS.findall(text))
    if emoji_count >= 5:
        score -= 0.18
        reasons.append("emojis_excessifs")
    elif emoji_count >= 3:
        score -= 0.08

    # ── 9. Questions multiples (biais personnel/rhetorique) ───────────────────
    if text.count("?") >= 3:
        score -= 0.08
        reasons.append("questions_multiples")

    score = max(0.0, min(1.0, score))
    is_claim = score >= 0.50
    reason = ", ".join(reasons) if reasons else "score_neutre"
    return is_claim, round(score, 3), reason


# ── Boilerplate MongoDB ───────────────────────────────────────────────────────

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


def _flush(ops: list[UpdateOne], col: Any) -> tuple[int, int]:
    if not ops:
        return 0, 0
    try:
        res = col.bulk_write(ops, ordered=False)
        return res.upserted_count, res.matched_count
    except BulkWriteError as exc:
        logging.warning("Bulk write warning: %s", exc.details)
        return 0, 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    _setup_logging()
    _load_environment()

    mongo_uri = _required_env("MONGO_URI")
    db_name = os.getenv("MONGO_DB", "bluesky")
    clean_col_name = os.getenv("MONGO_COLLECTION_CLEAN", "posts_clean")
    threshold = float(os.getenv("CLAIM_THRESHOLD", "0.5"))
    batch_size = int(os.getenv("CLAIM_BATCH_SIZE", "500"))

    client = MongoClient(mongo_uri)
    col = client[db_name][clean_col_name]

    total = col.count_documents({})
    logging.info(
        "Start claim filter: docs=%s threshold=%.2f version=%s",
        total, threshold, CLAIM_FILTER_VERSION,
    )

    filtered_at = datetime.now(timezone.utc).isoformat()
    ops: list[UpdateOne] = []
    processed = claims = non_claims = 0

    for doc in col.find({}, {"uri": 1, "text": 1, "clean_text": 1}):
        text = doc.get("text") or ""
        clean_text = doc.get("clean_text") or ""

        is_claim, claim_score, claim_reason = classify_claim(text, clean_text)

        if is_claim:
            claims += 1
        else:
            non_claims += 1

        ops.append(UpdateOne(
            {"uri": doc["uri"]},
            {"$set": {
                "is_claim": is_claim,
                "claim_score": claim_score,
                "claim_reason": claim_reason,
                "claim_filtered_at": filtered_at,
                "claim_filter_version": CLAIM_FILTER_VERSION,
            }},
        ))
        processed += 1

        if len(ops) >= batch_size:
            _flush(ops, col)
            ops = []
            logging.info(
                "Progress claim filter: %s/%s | claims=%s non_claims=%s",
                processed, total, claims, non_claims,
            )

    _flush(ops, col)

    logging.info(
        "Claim filter done: processed=%s claims=%s (%.1f%%) non_claims=%s (%.1f%%)",
        processed,
        claims, claims / max(processed, 1) * 100,
        non_claims, non_claims / max(processed, 1) * 100,
    )


if __name__ == "__main__":
    main()
