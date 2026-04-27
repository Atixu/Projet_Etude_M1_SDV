"""Nettoyage et normalisation de texte pour le pipeline NLP.

Strategie:
- FR : on garde les accents (utile pour modeles FR), on supprime emojis/symboles.
- EN et autres : normalisation complete, suppression accents.
- Dans les deux cas : URLs, mentions, hashtags retires.
"""

from __future__ import annotations

import re
import unicodedata


URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"@[\w.:-]+")
HASHTAG_RE = re.compile(r"#\w+")
MULTISPACE_RE = re.compile(r"\s+")
# Garde lettres (unicode), chiffres et espaces — supprime emojis et symboles.
SYMBOLS_RE = re.compile(r"[^\w\s]", re.UNICODE)
# Version stricte ASCII pour EN : ne garde que a-z, 0-9 et espaces.
NONASCII_RE = re.compile(r"[^a-z0-9\s]")


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


def clean_text(text: str, lang: str = "en") -> str:
    """Nettoie un texte brut.

    Args:
        text: Texte brut issu de Bluesky.
        lang: Code langue ISO 639-1 (ex: 'fr', 'en'). Par defaut 'en'.

    Returns:
        Texte normalise pret pour la vectorisation.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    t = text

    # 1. Retirer URLs, mentions, hashtags.
    t = URL_RE.sub(" ", t)
    t = MENTION_RE.sub(" ", t)
    t = HASHTAG_RE.sub(" ", t)

    # 2. Minuscules.
    t = t.lower()

    if lang == "fr":
        # Pour le FR on garde les accents, on retire seulement les symboles/emojis.
        t = SYMBOLS_RE.sub(" ", t)
    else:
        # Pour EN et autres : suppression des accents puis filtrage ASCII.
        t = _strip_accents(t)
        t = NONASCII_RE.sub(" ", t)

    # 3. Normaliser les espaces.
    t = MULTISPACE_RE.sub(" ", t).strip()

    return t


def extract_lang(langs: list[str] | None) -> str:
    """Retourne le premier code langue disponible, sinon 'unknown'."""
    if not langs:
        return "unknown"
    first = langs[0].lower().split("-")[0]  # 'fr-FR' -> 'fr'
    return first if first else "unknown"


def token_count(text: str) -> int:
    """Nombre approximatif de tokens (split par espaces)."""
    if not text:
        return 0
    return len(text.split())
