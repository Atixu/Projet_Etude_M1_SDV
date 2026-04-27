"""Partie 6 - Dashboard MVP (Streamlit) avec Agent IA (Groq/Llama3).

Run:
    streamlit run src/dashboard_app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient


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


@st.cache_data(ttl=120)
def load_posts_df() -> pd.DataFrame:
    _load_environment()
    mongo_uri = _required_env("MONGO_URI")
    db_name = os.getenv("MONGO_DB", "bluesky")
    clean_col_name = os.getenv("MONGO_COLLECTION_CLEAN", "posts_clean")

    client = MongoClient(mongo_uri)
    col = client[db_name][clean_col_name]

    projection = {
        "_id": 0,
        "uri": 1,
        "created_at": 1,
        "collected_at": 1,
        "lang": 1,
        "search_term": 1,
        "text": 1,
        "clean_text": 1,
        "credibility_score": 1,
        "final_credibility_score": 1,
        "final_alert_level": 1,
        "predicted_label": 1,
        "sentiment_label": 1,
        "sentiment_compound": 1,
        "dominant_emotion": 1,
        "explanation_text": 1,
    }

    docs = list(col.find({}, projection))
    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs)

    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)

    if "final_credibility_score" in df.columns:
        df["final_credibility_score"] = pd.to_numeric(
            df["final_credibility_score"], errors="coerce"
        ).fillna(0.0)

    for col_name in ["final_alert_level", "lang", "dominant_emotion", "sentiment_label"]:
        if col_name in df.columns:
            df[col_name] = df[col_name].fillna("unknown")

    return df


def render_kpis(df: pd.DataFrame) -> None:
    total = len(df)
    high = int((df["final_alert_level"] == "high").sum())
    medium = int((df["final_alert_level"] == "medium").sum())
    low = int((df["final_alert_level"] == "low").sum())
    avg_score = float(df["final_credibility_score"].mean()) if total else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Posts", f"{total:,}")
    c2.metric("Alerte High", high)
    c3.metric("Alerte Medium", medium)
    c4.metric("Alerte Low", low)
    c5.metric("Score moyen", f"{avg_score:.3f}")


def render_charts(df: pd.DataFrame) -> None:
    left, right = st.columns(2)

    with left:
        alert_df = (
            df["final_alert_level"].value_counts().rename_axis("alert").reset_index(name="count")
        )
        fig_alert = px.pie(
            alert_df,
            names="alert",
            values="count",
            title="Distribution des alertes finales",
            color="alert",
            color_discrete_map={"high": "#d7263d", "medium": "#f4a261", "low": "#2a9d8f"},
        )
        st.plotly_chart(fig_alert, width="stretch")

    with right:
        emo_df = (
            df["dominant_emotion"].value_counts().rename_axis("emotion").reset_index(name="count")
        )
        fig_emo = px.bar(
            emo_df,
            x="emotion",
            y="count",
            title="Emotions dominantes",
            color="emotion",
        )
        st.plotly_chart(fig_emo, width="stretch")

    lang_df = df["lang"].value_counts().rename_axis("lang").reset_index(name="count")
    fig_lang = px.bar(
        lang_df,
        x="lang",
        y="count",
        title="Repartition des langues",
        color="lang",
    )
    st.plotly_chart(fig_lang, width="stretch")

    if df["created_at"].notna().any():
        timeline_df = (
            df.dropna(subset=["created_at"])
            .set_index("created_at")
            .resample("D")
            .size()
            .rename("count")
            .reset_index()
        )
        fig_time = px.line(
            timeline_df,
            x="created_at",
            y="count",
            title="Volume de posts par jour",
        )
        st.plotly_chart(fig_time, width="stretch")


def build_data_context(df: pd.DataFrame) -> str:
    """Construit un résumé textuel des données pour le prompt système du LLM."""
    if df.empty:
        return "Aucune donnée disponible dans la base."

    total = len(df)
    alert_counts = df["final_alert_level"].value_counts().to_dict() if "final_alert_level" in df.columns else {}
    emotion_counts = df["dominant_emotion"].value_counts().head(6).to_dict() if "dominant_emotion" in df.columns else {}
    lang_counts = df["lang"].value_counts().to_dict() if "lang" in df.columns else {}
    avg_score = float(df["final_credibility_score"].mean()) if "final_credibility_score" in df.columns else 0.0
    top_terms = df["search_term"].value_counts().head(5).to_dict() if "search_term" in df.columns else {}

    high_posts = df[df["final_alert_level"] == "high"][["text", "explanation_text"]].head(3).to_dict("records") if "final_alert_level" in df.columns else []
    examples_text = "\n".join(
        f"  - \"{p.get('text', '')[:120]}...\" → {p.get('explanation_text', '')}"
        for p in high_posts
    )

    return f"""Tu es l'assistant IA du système Thumalien, un outil de détection de fake news sur Bluesky.
Tu analyses les posts collectés et tu aides les utilisateurs à comprendre les tendances de désinformation.

Données actuelles dans la base :
- Total posts analysés : {total}
- Répartition des alertes : {alert_counts}  (high = forte probabilité fake news)
- Score de crédibilité moyen : {avg_score:.3f}  (0 = très crédible, 1 = probablement fake)
- Émotions dominantes : {emotion_counts}
- Langues : {lang_counts}
- Mots-clés surveillés (top 5) : {top_terms}

Exemples de posts à forte alerte :
{examples_text}

Réponds toujours en français, de façon concise et factuelle. Si on te demande quelque chose hors de ce périmètre, redirige poliment vers les données disponibles."""


def render_chat(df: pd.DataFrame) -> None:
    """Onglet Agent IA — chatbot Groq/Llama3."""
    st.subheader("🤖 Agent IA — Analyse Thumalien")
    st.caption("Posez des questions sur les données de désinformation collectées sur Bluesky.")

    _load_environment()
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        st.warning(
            "Clé Groq manquante. Ajoute `GROQ_API_KEY=...` dans ton fichier `.env`.\n\n"
            "Crée un compte gratuit sur [console.groq.com](https://console.groq.com) → API Keys."
        )
        return

    try:
        from groq import Groq  # noqa: PLC0415
    except ImportError:
        st.error("`groq` non installé. Lance : `pip install groq`")
        return

    system_prompt = build_data_context(df)

    # Initialise l'historique dans la session
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Affiche l'historique
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input utilisateur
    user_input = st.chat_input("Ex: Combien de posts sont en alerte high ? Quelles émotions dominent ?")
    if not user_input:
        return

    # Affiche la question
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Appel Groq
    with st.chat_message("assistant"):
        with st.spinner("Analyse en cours..."):
            try:
                client = Groq(api_key=groq_api_key)
                messages = [
                    {"role": "system", "content": system_prompt},
                    *st.session_state.chat_history,
                ]
                response = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=messages,
                    max_tokens=512,
                    temperature=0.3,
                )
                answer = response.choices[0].message.content
            except Exception as exc:  # noqa: BLE001
                answer = f"❌ Erreur lors de l'appel Groq : {exc}"

        st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # Bouton reset
    if st.session_state.chat_history:
        if st.button("🗑️ Effacer la conversation", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Thumalien - Dashboard MVP",
        page_icon="📊",
        layout="wide",
    )

    st.title("Thumalien - Dashboard Fake News MVP")
    st.caption("Vue synthese + detail post pour aide au fact-checking")

    df = load_posts_df()
    if df.empty:
        st.warning("Aucune donnee disponible dans posts_clean.")
        st.stop()

    tab1, tab2 = st.tabs(["📊 Dashboard", "🤖 Agent IA"])

    # ---- Sidebar filters (affect tab1 only) ----
    st.sidebar.header("Filtres")

    languages = sorted(df["lang"].dropna().unique().tolist())
    selected_langs = st.sidebar.multiselect("Langues", languages, default=languages)

    alert_levels = ["high", "medium", "low"]
    selected_alerts = st.sidebar.multiselect(
        "Niveaux d'alerte", alert_levels, default=alert_levels
    )

    emotions = sorted(df["dominant_emotion"].dropna().unique().tolist())
    selected_emotions = st.sidebar.multiselect(
        "Emotions dominantes", emotions, default=emotions
    )

    if df["created_at"].notna().any():
        min_date = df["created_at"].min().date()
        max_date = df["created_at"].max().date()
        date_range = st.sidebar.date_input(
            "Periode",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        date_range = None

    query = st.sidebar.text_input("Recherche texte")

    filtered = df.copy()
    filtered = filtered[filtered["lang"].isin(selected_langs)]
    filtered = filtered[filtered["final_alert_level"].isin(selected_alerts)]
    filtered = filtered[filtered["dominant_emotion"].isin(selected_emotions)]

    if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        if "created_at" in filtered.columns:
            filtered = filtered[
                (filtered["created_at"].dt.date >= start_date.date())
                & (filtered["created_at"].dt.date <= end_date.date())
            ]

    if query:
        mask = (
            filtered["text"].fillna("").str.contains(query, case=False, regex=False)
            | filtered["clean_text"].fillna("").str.contains(query, case=False, regex=False)
            | filtered["explanation_text"].fillna("").str.contains(query, case=False, regex=False)
        )
        filtered = filtered[mask]

    with tab1:
        st.subheader("Vue synthese")
        render_kpis(filtered)
        render_charts(filtered)

        st.subheader("Vue detail")

        display_cols = [
            "uri",
            "created_at",
            "lang",
            "search_term",
            "final_alert_level",
            "final_credibility_score",
            "predicted_label",
            "sentiment_label",
            "dominant_emotion",
        ]

        existing_display_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(
            filtered[existing_display_cols].sort_values(
                by=["final_alert_level", "final_credibility_score"],
                ascending=[True, True],
            ),
            width="stretch",
            height=420,
        )

        st.markdown("---")
        st.markdown("### Post selectionne")

        selected_uri = st.selectbox("URI", options=filtered["uri"].tolist())
        selected = filtered[filtered["uri"] == selected_uri].iloc[0]

        st.write("**Texte original**")
        st.write(selected.get("text", ""))

        st.write("**Explication**")
        st.write(selected.get("explanation_text", ""))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Score final", f"{selected.get('final_credibility_score', 0.0):.3f}")
        m2.metric("Alerte", str(selected.get("final_alert_level", "unknown")))
        m3.metric("Sentiment", str(selected.get("sentiment_label", "unknown")))
        m4.metric("Emotion", str(selected.get("dominant_emotion", "unknown")))

    with tab2:
        render_chat(df)


if __name__ == "__main__":
    main()
