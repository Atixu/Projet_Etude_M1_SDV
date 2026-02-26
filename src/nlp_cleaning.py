import re
import unicodedata

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"@\w+")
HASHTAG_RE = re.compile(r"#\w+")
MULTISPACE_RE = re.compile(r"\s+")

def strip_accents(s: str) -> str:
    # enlève les accents (é -> e)
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )

def clean_text(text: str) -> str:
    if not text:
        return ""

    t = text

    # 1) URLs / mentions / hashtags
    t = URL_RE.sub(" ", t)
    t = MENTION_RE.sub(" ", t)
    t = HASHTAG_RE.sub(" ", t)

    # 2) minuscules
    t = t.lower()

    # 3) normalisation unicode + suppression accents
    t = strip_accents(t)

    # 4) enlever emojis / symboles (garde lettres/chiffres/espaces)
    # -> supprime tout ce qui n'est pas lettre, chiffre, espace
    t = re.sub(r"[^a-z0-9\s]", " ", t)

    # 5) espaces
    t = MULTISPACE_RE.sub(" ", t).strip()

    return t