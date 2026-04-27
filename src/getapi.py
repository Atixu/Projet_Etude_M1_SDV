"""Collecte des posts Bluesky par recherche de mots-cles et stockage brut dans MongoDB.

Mode de collecte: app.bsky.feed.searchPosts sur une liste de termes
relatifs a la desinformation / fake news (FR et EN).

Variables d'environnement requises:
- BLUESKY_IDENTIFIER
- BLUESKY_APP_PASSWORD
- MONGO_URI

Variables optionnelles:
- MONGO_DB (defaut: bluesky)
- MONGO_COLLECTION_RAW (defaut: posts_raw)
- BLUESKY_BASE_URL (defaut: https://bsky.social)
- BLUESKY_LIMIT (defaut: 100 par terme)
- BLUESKY_MAX_PAGES (defaut: 3 par terme)
- BLUESKY_SEARCH_TERMS (defaut: liste integree, separee par |)
- DOTENV_PATH (chemin vers .env si necessaire)
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def _load_environment() -> None:
    # Resolve .env from project root to support both local runs and Airflow container runs.
    dotenv_path = os.getenv("DOTENV_PATH")
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path)
        return

    project_root_env = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=project_root_env)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer") from exc

    if value <= 0:
        raise RuntimeError(f"Environment variable {name} must be > 0")
    return value


def _http_session() -> requests.Session:
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _raise_for_status(response: Response, context: str) -> None:
    if response.ok:
        return
    body = response.text[:500]
    raise RuntimeError(
        f"{context} failed with status={response.status_code} body={body}"
    )


def create_bluesky_session(
    http: requests.Session,
    base_url: str,
    identifier: str,
    app_password: str,
) -> Dict[str, Any]:
    url = f"{base_url}/xrpc/com.atproto.server.createSession"
    payload = {"identifier": identifier, "password": app_password}
    resp = http.post(url, json=payload, timeout=30)
    _raise_for_status(resp, "createSession")
    return resp.json()


def fetch_search_posts(
    http: requests.Session,
    base_url: str,
    access_jwt: str,
    query: str,
    limit: int,
    max_pages: int,
) -> List[Dict[str, Any]]:
    """Collecte des posts via app.bsky.feed.searchPosts pour un terme donne."""
    url = f"{base_url}/xrpc/app.bsky.feed.searchPosts"
    headers = {"Authorization": f"Bearer {access_jwt}"}
    cursor: Optional[str] = None
    collected: List[Dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        params: Dict[str, Any] = {"q": query, "limit": min(limit, 100)}
        if cursor:
            params["cursor"] = cursor

        resp = http.get(url, params=params, headers=headers, timeout=30)
        _raise_for_status(resp, f"searchPosts q='{query}' page={page}")

        payload = resp.json()
        posts = payload.get("posts", [])
        collected.extend(posts)
        cursor = payload.get("cursor")

        logging.info(
            "searchPosts q='%s' page=%s: items=%s cumulative=%s",
            query,
            page,
            len(posts),
            len(collected),
        )

        if not cursor or not posts:
            break

        time.sleep(0.3)

    return collected


def save_raw_posts(
    mongo_uri: str,
    db_name: str,
    collection_name: str,
    posts: List[Dict[str, Any]],
    search_term: str,
) -> Dict[str, int]:
    client = MongoClient(mongo_uri)
    collection = client[db_name][collection_name]

    collection.create_index("uri", unique=True)

    collected_at = datetime.now(timezone.utc).isoformat()
    ops: List[UpdateOne] = []

    for post in posts:
        post_uri = post.get("uri")
        if not post_uri:
            continue

        doc = {
            "uri": post_uri,
            "post": post,
            "feed_context": {
                "source": "app.bsky.feed.searchPosts",
                "search_term": search_term,
                "collected_at": collected_at,
            },
        }
        ops.append(UpdateOne({"uri": post_uri}, {"$set": doc}, upsert=True))

    if not ops:
        return {"matched": 0, "modified": 0, "upserted": 0}

    try:
        result = collection.bulk_write(ops, ordered=False)
        return {
            "matched": result.matched_count,
            "modified": result.modified_count,
            "upserted": result.upserted_count,
        }
    except BulkWriteError as exc:
        logging.warning("Bulk write warning: %s", exc.details)
        return {"matched": 0, "modified": 0, "upserted": 0}


# Termes de recherche par defaut orientes fake news / desinformation FR + EN.
DEFAULT_SEARCH_TERMS = [
    "fake news",
    "desinformation",
    "complot",
    "intox",
    "misinformation",
    "disinformation",
    "fact check",
    "rumeur",
    "hoax",
    "propagande",
]


def main() -> None:
    _setup_logging()
    _load_environment()

    base_url = os.getenv("BLUESKY_BASE_URL", "https://bsky.social").rstrip("/")
    identifier = _required_env("BLUESKY_IDENTIFIER")
    app_password = _required_env("BLUESKY_APP_PASSWORD")

    limit = _int_env("BLUESKY_LIMIT", 100)
    max_pages = _int_env("BLUESKY_MAX_PAGES", 3)

    mongo_uri = _required_env("MONGO_URI")
    db_name = os.getenv("MONGO_DB", "bluesky")
    raw_collection = os.getenv("MONGO_COLLECTION_RAW", "posts_raw")

    raw_terms = os.getenv("BLUESKY_SEARCH_TERMS", "")
    search_terms = [t.strip() for t in raw_terms.split("|") if t.strip()] or DEFAULT_SEARCH_TERMS

    http = _http_session()
    bsky_session = create_bluesky_session(http, base_url, identifier, app_password)
    access_jwt = bsky_session.get("accessJwt")
    if not access_jwt:
        raise RuntimeError("No accessJwt returned by Bluesky createSession")

    logging.info(
        "Start collection: terms=%s limit=%s max_pages=%s db=%s collection=%s",
        search_terms,
        limit,
        max_pages,
        db_name,
        raw_collection,
    )

    total_fetched = 0
    total_upserted = 0

    for term in search_terms:
        posts = fetch_search_posts(
            http=http,
            base_url=base_url,
            access_jwt=access_jwt,
            query=term,
            limit=limit,
            max_pages=max_pages,
        )

        stats = save_raw_posts(
            mongo_uri=mongo_uri,
            db_name=db_name,
            collection_name=raw_collection,
            posts=posts,
            search_term=term,
        )

        total_fetched += len(posts)
        total_upserted += stats["upserted"]

        logging.info(
            "Term '%s' done: fetched=%s upserted=%s matched=%s",
            term,
            len(posts),
            stats["upserted"],
            stats["matched"],
        )

    logging.info(
        "Collection complete: total_fetched=%s total_upserted=%s terms=%s",
        total_fetched,
        total_upserted,
        len(search_terms),
    )


if __name__ == "__main__":
    main()
