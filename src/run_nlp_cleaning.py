import os
from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

from nlp_cleaning import clean_text

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB", "bluesky")
RAW_COL = os.getenv("MONGO_COLLECTION_RAW", "posts_raw")
CLEAN_COL = os.getenv("MONGO_COLLECTION_CLEAN", "posts_clean")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
raw = db[RAW_COL]
clean = db[CLEAN_COL]

# Index recommandé : évite doublons
clean.create_index("uri", unique=True)

# On prend les derniers posts (ou ceux pas encore nettoyés)
cursor = raw.find(
    {"post.record.text": {"$exists": True, "$ne": None}},
    {"post.record.text": 1, "post.uri": 1, "post.author.handle": 1, "post.record.createdAt": 1}
).sort([("_id", -1)]).limit(200)  # tu peux augmenter

ops = []
now = datetime.now(timezone.utc).isoformat()

for doc in cursor:
    # Selon ton format raw, adapte le chemin :
    # Ici je suppose que tu stockes le JSON "item" complet dans un champ raw.  
    # Si ton raw est différent, je te le corrige.
    post = doc.get("post", {})
    record = post.get("record", {})
    author = post.get("author", {})

    uri = post.get("uri")
    text = record.get("text", "")

    cleaned = clean_text(text)

    out = {
        "uri": uri,
        "author_handle": author.get("handle"),
        "createdAt": record.get("createdAt"),
        "text": text,
        "clean_text": cleaned,
        "cleanedAt": now,
        "pipeline": "nlp_cleaning_v1",
    }

    ops.append(
        UpdateOne({"uri": uri}, {"$set": out}, upsert=True)
    )

if ops:
    res = clean.bulk_write(ops, ordered=False)
    print("Docs upsert:", res.upserted_count, "| matched:", res.matched_count)
else:
    print("Aucun doc à traiter.")