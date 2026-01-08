#Tentative de récupération de l'API
import urllib.request
import json

url = "https://bsky.social/xrpc/com.atproto.server.createSession"

data = {
    "identifier": "atixu.bsky.social",
    "password": "nayw-y7ol-vgn2-fu6e"
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urllib.request.urlopen(req) as response:
    session = json.loads(response.read().decode("utf-8"))

print(session)
