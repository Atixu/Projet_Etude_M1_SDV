"""Définition du pipeline Kedro NLP Cleaning.

Ce pipeline orchestre les 7 étapes de nettoyage NLP :
  extract → clean → detect_lang → normalize → tokenize → lemmatize → load

Chaque node est une fonction pure (nodes.py).
Les datasets intermédiaires sont catalogués dans conf/base/catalog.yml.
Les paramètres viennent de conf/base/parameters_nlp_cleaning.yml.

Lancement :
    cd etl-bluesky
    kedro run --pipeline nlp_cleaning
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    clean_text_node,
    detect_language_node,
    extract_raw_posts,
    lemmatize_text_node,
    load_clean_posts,
    normalize_text_node,
    tokenize_text_node,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            # ----------------------------------------------------------------
            # Étape 1 : Extraction depuis MongoDB posts_raw
            # ----------------------------------------------------------------
            node(
                func=extract_raw_posts,
                inputs=[
                    "params:mongo_uri",
                    "params:database",
                    "params:raw_collection",
                ],
                outputs="raw_posts_df",
                name="extract_raw_posts_node",
                tags=["extract"],
            ),
            # ----------------------------------------------------------------
            # Étape 2 : Nettoyage — URLs, mentions, hashtags
            # ----------------------------------------------------------------
            node(
                func=clean_text_node,
                inputs="raw_posts_df",
                outputs="cleaned_posts_df",
                name="clean_text_node",
                tags=["clean"],
            ),
            # ----------------------------------------------------------------
            # Étape 3 : Détection de langue — filtre anglais uniquement
            # ----------------------------------------------------------------
            node(
                func=detect_language_node,
                inputs=["cleaned_posts_df", "params:target_lang"],
                outputs="lang_filtered_df",
                name="detect_language_node",
                tags=["clean"],
            ),
            # ----------------------------------------------------------------
            # Étape 4 : Normalisation — minuscules, accents, ASCII
            # ----------------------------------------------------------------
            node(
                func=normalize_text_node,
                inputs="lang_filtered_df",
                outputs="normalized_posts_df",
                name="normalize_text_node",
                tags=["normalize"],
            ),
            # ----------------------------------------------------------------
            # Étape 5 : Tokenisation — découpage en mots
            # ----------------------------------------------------------------
            node(
                func=tokenize_text_node,
                inputs=["normalized_posts_df", "params:min_token_count"],
                outputs="tokenized_posts_df",
                name="tokenize_text_node",
                tags=["tokenize"],
            ),
            # ----------------------------------------------------------------
            # Étape 6 : Lemmatisation — réduction à la forme canonique
            # ----------------------------------------------------------------
            node(
                func=lemmatize_text_node,
                inputs=["tokenized_posts_df", "params:use_nltk_lemmatizer"],
                outputs="lemmatized_posts_df",
                name="lemmatize_text_node",
                tags=["lemmatize"],
            ),
            # ----------------------------------------------------------------
            # Étape 7 : Chargement dans MongoDB posts_clean_kedro
            # ----------------------------------------------------------------
            node(
                func=load_clean_posts,
                inputs=[
                    "lemmatized_posts_df",
                    "params:mongo_uri",
                    "params:database",
                    "params:clean_collection",
                ],
                outputs="nlp_pipeline_summary",
                name="load_clean_posts_node",
                tags=["load"],
            ),
        ]
    )
