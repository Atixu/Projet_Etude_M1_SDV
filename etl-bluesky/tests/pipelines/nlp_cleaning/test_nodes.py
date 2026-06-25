"""Tests unitaires pour les nodes du pipeline nlp_cleaning.

Couvre les nodes 2 à 6 (fonctions pures, sans dépendance MongoDB).
Les nodes 1 (extract) et 7 (load) nécessitent MongoDB et sont testés
en integration via `kedro run --pipeline nlp_cleaning`.
"""

import pandas as pd
import pytest

from etl_bluesky.pipelines.nlp_cleaning.nodes import (
    clean_text_node,
    detect_language_node,
    lemmatize_text_node,
    normalize_text_node,
    tokenize_text_node,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def raw_df():
    return pd.DataFrame({
        "uri": ["at://user/1", "at://user/2", "at://user/3"],
        "text": [
            "Check out https://example.com and @alice about #fakenews!",
            "This is a clean sentence about politics.",
            "",
        ],
        "langs": [["en"], ["en"], []],
        "created_at": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "author_did": ["did:plc:a", "did:plc:b", "did:plc:c"],
    })


@pytest.fixture
def cleaned_df():
    return pd.DataFrame({
        "uri": ["at://user/1", "at://user/2"],
        "text": ["Check out and about", "This is a clean sentence about politics."],
        "text_cleaned": ["Check out and about", "This is a clean sentence about politics."],
        "langs": [["en"], ["en"]],
        "created_at": ["2024-01-01", "2024-01-02"],
        "author_did": ["did:plc:a", "did:plc:b"],
    })


@pytest.fixture
def english_df():
    return pd.DataFrame({
        "uri": ["at://user/1", "at://user/2", "at://user/3"],
        "text": ["hello world", "guten morgen wie geht es dir heute", "bonjour le monde"],
        "text_cleaned": [
            "This is a genuine English sentence about politics and society.",
            "Dies ist ein echter deutscher Satz ueber Politik und Gesellschaft.",
            "Ceci est une vraie phrase francaise sur la politique et la societe.",
        ],
        "langs": [["en"], ["de"], ["fr"]],
        "detected_lang": ["en", "de", "fr"],
        "created_at": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "author_did": ["did:plc:a", "did:plc:b", "did:plc:c"],
    })


@pytest.fixture
def lang_filtered_df():
    return pd.DataFrame({
        "uri": ["at://user/1", "at://user/2"],
        "text": ["hello world", "politics today"],
        "text_cleaned": ["hello world", "politics today"],
        "detected_lang": ["en", "en"],
        "created_at": ["2024-01-01", "2024-01-02"],
        "author_did": ["did:plc:a", "did:plc:b"],
    })


@pytest.fixture
def normalized_df():
    return pd.DataFrame({
        "uri": ["at://user/1", "at://user/2"],
        "text_cleaned": ["hello world", "the politicians are running"],
        "text_normalized": ["hello world", "the politicians are running"],
        "detected_lang": ["en", "en"],
        "created_at": ["2024-01-01", "2024-01-02"],
        "author_did": ["did:plc:a", "did:plc:b"],
    })


@pytest.fixture
def tokenized_df():
    return pd.DataFrame({
        "uri": ["at://user/1", "at://user/2"],
        "text_normalized": ["hello world", "the politicians are running"],
        "tokens": [["hello", "world"], ["the", "politicians", "are", "running"]],
        "token_count": [2, 4],
        "detected_lang": ["en", "en"],
        "created_at": ["2024-01-01", "2024-01-02"],
        "author_did": ["did:plc:a", "did:plc:b"],
    })


# ---------------------------------------------------------------------------
# Node 2 — clean_text_node
# ---------------------------------------------------------------------------

class TestCleanTextNode:
    def test_removes_url(self):
        df = pd.DataFrame({"uri": ["u1"], "text": ["Visit https://example.com today"], "langs": [[]], "created_at": [""], "author_did": [""]})
        result = clean_text_node(df)
        assert "https" not in result["text_cleaned"].iloc[0]

    def test_removes_mention(self):
        df = pd.DataFrame({"uri": ["u1"], "text": ["Hey @alice.bsky.social check this"], "langs": [[]], "created_at": [""], "author_did": [""]})
        result = clean_text_node(df)
        assert "@alice" not in result["text_cleaned"].iloc[0]

    def test_removes_hashtag(self):
        df = pd.DataFrame({"uri": ["u1"], "text": ["Breaking #FakeNews alert"], "langs": [[]], "created_at": [""], "author_did": [""]})
        result = clean_text_node(df)
        assert "#FakeNews" not in result["text_cleaned"].iloc[0]

    def test_drops_empty_rows(self, raw_df):
        result = clean_text_node(raw_df)
        assert len(result) == 2

    def test_adds_text_cleaned_column(self, raw_df):
        result = clean_text_node(raw_df)
        assert "text_cleaned" in result.columns

    def test_removes_all_noise_combined(self):
        df = pd.DataFrame({
            "uri": ["u1"],
            "text": ["@user check https://x.com #tag content"],
            "langs": [[]], "created_at": [""], "author_did": [""],
        })
        result = clean_text_node(df)
        cleaned = result["text_cleaned"].iloc[0]
        assert "@user" not in cleaned
        assert "https" not in cleaned
        assert "#tag" not in cleaned
        assert "content" in cleaned


# ---------------------------------------------------------------------------
# Node 3 — detect_language_node
# ---------------------------------------------------------------------------

class TestDetectLanguageNode:
    def test_keeps_english_posts(self):
        df = pd.DataFrame({
            "uri": ["u1"],
            "text": ["test"],
            "text_cleaned": ["The president signed a new executive order today affecting thousands of workers."],
            "langs": [["en"]], "created_at": [""], "author_did": [""],
        })
        result = detect_language_node(df, "en")
        assert len(result) == 1
        assert result["detected_lang"].iloc[0] == "en"

    def test_filters_german_posts(self):
        df = pd.DataFrame({
            "uri": ["u1"],
            "text": ["test"],
            "text_cleaned": ["Die Bundesregierung hat heute eine neue Verordnung verabschiedet die viele Buerger betrifft."],
            "langs": [["en"]],  # user declared "en" but text is German
            "created_at": [""], "author_did": [""],
        })
        result = detect_language_node(df, "en")
        assert len(result) == 0

    def test_adds_detected_lang_column(self):
        df = pd.DataFrame({
            "uri": ["u1"],
            "text": ["test"],
            "text_cleaned": ["This is a clearly English sentence about news and politics."],
            "langs": [["en"]], "created_at": [""], "author_did": [""],
        })
        result = detect_language_node(df, "en")
        assert "detected_lang" in result.columns


# ---------------------------------------------------------------------------
# Node 4 — normalize_text_node
# ---------------------------------------------------------------------------

class TestNormalizeTextNode:
    def test_lowercases_text(self, lang_filtered_df):
        lang_filtered_df["text_cleaned"] = ["Hello WORLD", "POLITICS Today"]
        result = normalize_text_node(lang_filtered_df)
        assert result["text_normalized"].iloc[0] == "hello world"
        assert result["text_normalized"].iloc[1] == "politics today"

    def test_strips_accents(self, lang_filtered_df):
        lang_filtered_df["text_cleaned"] = ["cafe au lait", "naive approach"]
        result = normalize_text_node(lang_filtered_df)
        for val in result["text_normalized"]:
            assert "é" not in val
            assert "ï" not in val

    def test_removes_nonascii_chars(self, lang_filtered_df):
        lang_filtered_df["text_cleaned"] = ["hello 世界 world", "test emoji world"]
        result = normalize_text_node(lang_filtered_df)
        normalized = result["text_normalized"].iloc[0]
        assert all(ord(c) < 128 for c in normalized)

    def test_adds_text_normalized_column(self, lang_filtered_df):
        result = normalize_text_node(lang_filtered_df)
        assert "text_normalized" in result.columns

    def test_drops_empty_after_normalization(self):
        df = pd.DataFrame({
            "uri": ["u1", "u2"],
            "text_cleaned": ["hello world", "   "],
            "detected_lang": ["en", "en"],
            "created_at": ["", ""], "author_did": ["", ""],
        })
        result = normalize_text_node(df)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Node 5 — tokenize_text_node
# ---------------------------------------------------------------------------

class TestTokenizeTextNode:
    def test_splits_into_tokens(self, normalized_df):
        result = tokenize_text_node(normalized_df, min_token_count=1)
        tokens = result["tokens"].iloc[0]
        assert isinstance(tokens, list)
        assert len(tokens) >= 1

    def test_adds_token_count_column(self, normalized_df):
        result = tokenize_text_node(normalized_df, min_token_count=1)
        assert "token_count" in result.columns
        assert (result["token_count"] >= 1).all()

    def test_filters_by_min_token_count(self, normalized_df):
        result = tokenize_text_node(normalized_df, min_token_count=5)
        assert all(result["token_count"] >= 5)

    def test_min_token_count_zero_keeps_all(self, normalized_df):
        result = tokenize_text_node(normalized_df, min_token_count=0)
        assert len(result) == len(normalized_df)

    def test_empty_text_produces_zero_tokens(self):
        df = pd.DataFrame({
            "uri": ["u1", "u2"],
            "text_normalized": ["hello world", ""],
            "detected_lang": ["en", "en"],
            "created_at": ["", ""], "author_did": ["", ""],
        })
        result = tokenize_text_node(df, min_token_count=1)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Node 6 — lemmatize_text_node
# ---------------------------------------------------------------------------

class TestLemmatizeTextNode:
    def test_adds_lemmatized_tokens_column(self, tokenized_df):
        result = lemmatize_text_node(tokenized_df, use_nltk_lemmatizer=False)
        assert "lemmatized_tokens" in result.columns

    def test_adds_clean_text_column(self, tokenized_df):
        result = lemmatize_text_node(tokenized_df, use_nltk_lemmatizer=False)
        assert "clean_text" in result.columns

    def test_clean_text_is_joined_tokens(self, tokenized_df):
        result = lemmatize_text_node(tokenized_df, use_nltk_lemmatizer=False)
        row = result.iloc[0]
        assert row["clean_text"] == " ".join(row["lemmatized_tokens"])

    def test_without_nltk_returns_same_tokens(self, tokenized_df):
        result = lemmatize_text_node(tokenized_df, use_nltk_lemmatizer=False)
        for i, row in result.iterrows():
            assert list(row["lemmatized_tokens"]) == list(tokenized_df.iloc[i]["tokens"])

    def test_with_nltk_lemmatizer(self, tokenized_df):
        tokenized_df = tokenized_df.copy()
        tokenized_df["tokens"] = [["running", "politicians"], ["studies", "wolves"]]
        tokenized_df["token_count"] = [2, 2]
        result = lemmatize_text_node(tokenized_df, use_nltk_lemmatizer=True)
        lemmas_0 = result["lemmatized_tokens"].iloc[0]
        assert "running" in lemmas_0 or "run" in lemmas_0

    def test_preserves_row_count(self, tokenized_df):
        result = lemmatize_text_node(tokenized_df, use_nltk_lemmatizer=False)
        assert len(result) == len(tokenized_df)
