"""Baseline emotion analysis for FR/EN social posts.

This module combines:
- Lexicon-based emotion scoring (anger, fear, sadness, joy, surprise, humor)
- VADER sentiment polarity for a robust baseline signal
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict

TOKEN_RE = re.compile(r"\b\w+\b", re.UNICODE)

# Small bilingual lexicons for a baseline MVP.
EMOTION_LEXICONS = {
    "anger": {
        "angry", "rage", "furious", "hate", "outrage", "violence", "mad",
        "colere", "haine", "furieux", "furieuse", "rage", "violent", "violente",
    },
    "fear": {
        "fear", "scared", "panic", "threat", "danger", "anxiety", "terror",
        "peur", "panique", "menace", "danger", "anxiete", "terreur", "angoisse",
    },
    "sadness": {
        "sad", "grief", "cry", "depressed", "hopeless", "miserable",
        "triste", "tristesse", "deprime", "depression", "desespoir", "malheureux",
    },
    "joy": {
        "joy", "happy", "great", "love", "hope", "relief", "awesome",
        "joie", "heureux", "heureuse", "super", "espoir", "soulagement", "genial",
    },
    "surprise": {
        "surprised", "shock", "shocking", "unexpected", "wow", "amazing",
        "surpris", "surprise", "choc", "choquant", "incroyable", "improbable",
    },
    "humor": {
        "lol", "lmao", "rofl", "haha", "funny", "joke", "meme", "xd",
        "mdr", "ptdr", "blague", "drole", "humour", "rigole", "rire",
    },
}


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return TOKEN_RE.findall(text.lower())


def emotion_scores(text: str) -> Dict[str, float]:
    tokens = tokenize(text)
    if not tokens:
        return {k: 0.0 for k in EMOTION_LEXICONS}

    token_counts = Counter(tokens)
    total = len(tokens)
    scores: Dict[str, float] = {}

    for emotion, lexicon in EMOTION_LEXICONS.items():
        hit_count = sum(token_counts[w] for w in lexicon if w in token_counts)
        scores[emotion] = round(hit_count / total, 4)

    return scores


def dominant_emotion(scores: Dict[str, float]) -> str:
    if not scores:
        return "neutral"
    emo, value = max(scores.items(), key=lambda kv: kv[1])
    if value <= 0:
        return "neutral"
    return emo
