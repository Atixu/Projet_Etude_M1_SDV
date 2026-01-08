#Test de l'API
import os
import json
import urllib.request
from datetime import datetime, timezone

from pymongo import MongoClient, UpdateOne

# =========================
# CONFIG 
# =========================
BSKY_IDENTIFIER = "atixu.bsky.social"
BSKY_APP_PASSWORD = "nayw-y7ol-vgn2-fu6e"

MONGO_URI = "mongodb+srv://Atixu:AtLAO9ddWIkac24K@projetm1data.2o1upoi.mongodb.net/"
DB_NAME = "ProjetM1Data"
COLLECTION_RAW = "posts_raw"

# =========================
# 1) LOGIN BLUESKY
# =========================
login_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
login_data = {"identifier": BSKY_IDENTIFIER, "password": BSKY_APP_PASSWORD}

req = urllib.request.Request(
    login_url,
    data=json.dumps(login_data).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req) as response:
    session = json.loads(response.read().decode("utf-8"))

access_token = session["accessJwt"]
pds = session["didDoc"]["service"][0]["serviceEndpoint"]

# =========================
# 2) GET TIMELINE (10 posts max)
# =========================
timeline_url = f"{pds}/xrpc/app.bsky.feed.getTimeline?limit=10"
req = urllib.request.Request(
    timeline_url,
    headers={"Authorization": f"Bearer {access_token}"},
)

with urllib.request.urlopen(req) as response:
    timeline = json.loads(response.read().decode("utf-8"))

feed = timeline.get("feed", [])
print("Posts reçus :", len(feed))

# =========================
# 3) CONNECT MONGO
# =========================
client = MongoClient(MONGO_URI)
col = client[DB_NAME][COLLECTION_RAW]

# (Recommandé) index unique pour éviter les doublons
# uri est un bon identifiant stable côté ATProto
col.create_index("uri", unique=True)

# =========================
# 4) UPSERT (évite les doublons)
# =========================
now = datetime.now(timezone.utc)

ops = []
for item in feed:
    post = item.get("post", {})
    record = post.get("record", {})
    author = post.get("author", {})

    doc = {
        "uri": post.get("uri"),
        "cid": post.get("cid"),
        "author_handle": author.get("handle"),
        "author_did": author.get("did"),
        "createdAt": record.get("createdAt"),
        "text": record.get("text"),
        "raw": item,  # on garde le RAW complet (pratique pour debug)
        "ingestedAt": now.isoformat(),
        "source": "app.bsky.feed.getTimeline",
    }

    ops.append(
        UpdateOne(
            {"uri": doc["uri"]},
            {"$setOnInsert": doc},
            upsert=True,
        )
    )

if ops:
    res = col.bulk_write(ops, ordered=False)
    print("Insertés :", res.upserted_count, "| Déjà présents :", (len(ops) - res.upserted_count))
else:
    print("Aucun post à insérer.")
