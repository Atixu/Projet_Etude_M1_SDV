#Test de l'API

import urllib.request
import json

# =========================
# 1. AUTHENTIFICATION
# =========================

login_url = "https://bsky.social/xrpc/com.atproto.server.createSession"

login_data = {
    "identifier": "atixu.bsky.social",
    "password": "nayw-y7ol-vgn2-fu6e"
}

req = urllib.request.Request(
    login_url,
    data=json.dumps(login_data).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urllib.request.urlopen(req) as response:
    session = json.loads(response.read().decode("utf-8"))

access_token = session["accessJwt"]
pds = session["didDoc"]["service"][0]["serviceEndpoint"]

print("Auth OK :", session["handle"])

# =========================
# 2. EXTRACTION – 10 POSTS
# =========================

timeline_url = f"{pds}/xrpc/app.bsky.feed.getTimeline?limit=10"

req = urllib.request.Request(
    timeline_url,
    headers={"Authorization": f"Bearer {access_token}"}
)

with urllib.request.urlopen(req) as response:
    timeline = json.loads(response.read().decode("utf-8"))

print(f"{len(timeline['feed'])} posts récupérés\n")

# =========================
# 3. AFFICHAGE STRUCTURÉ
# =========================

for i, item in enumerate(timeline["feed"], start=1):
    post = item["post"]
    text = post["record"].get("text", "")
    author = post["author"].get("handle", "")
    created_at = post["record"].get("createdAt", "")

    print(f"Post {i}")
    print("Auteur :", author)
    print("Date   :", created_at)
    print("Texte  :", text.replace("\n", " "))
    print("-" * 50)
