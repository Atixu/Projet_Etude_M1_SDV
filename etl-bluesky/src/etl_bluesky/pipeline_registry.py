"""Project pipelines — registre des pipelines Kedro."""

from kedro.pipeline import Pipeline

from etl_bluesky.pipelines.nlp_cleaning import create_pipeline as nlp_pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Enregistre les pipelines du projet.

    Returns:
        Dictionnaire {nom: Pipeline}.
    """
    nlp_cleaning = nlp_pipeline()

    return {
        "nlp_cleaning": nlp_cleaning,
        "__default__": nlp_cleaning,
    }
