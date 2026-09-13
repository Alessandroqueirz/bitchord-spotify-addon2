from flask import Flask, jsonify, request
import requests
import re
import time

app = Flask(__name__)

# Cache do token anonimo
_cached_token = {"token": None, "expires_at": 0}

def get_anonymous_spotify_token():
    """
    Pega token anonimo do proprio web player do Spotify, sem precisar de Client ID.
    Funciona mesmo sem conta Premium e sem criar app.
    Baseado no projeto noauth / spotipy-anon
    """
    global _cached_token
    now = time.time()
    if _cached_token["token"] and now < _cached_token["expires_at"] - 60:
        return _cached_token["token"]

    try:
        # Spotify web player injeta um accessToken na página de search
        # Esse método foi usado por kaangiray26/noauth
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html"
        }
        # Pede a página de busca que contém o token
        r = requests.get("https://open.spotify.com/search", headers=headers, timeout=10)
        # Procura por "accessToken":"xxxx"
        m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', r.text)
        if m:
            token = m.group(1)
            # Token anonimo dura ~ 1h
            _cached_token["token"] = token
            _cached_token["expires_at"] = now + 3600
            return token

        # Fallback 2: tenta endpoint antigo do web-player
        r2 = requests.get("https://open.spotify.com/get_access_token?reason=transport&productType=web-player", headers=headers, timeout=10)
        if r2.status_code == 200:
            data = r2.json()
            token = data.get("accessToken")
            if token:
                _cached_token["token"] = token
                _cached_token["expires_at"] = now + 3600
                return token

    except Exception as e:
        print(f"Erro ao pegar token anonimo: {e}")

    return None

@app.route("/")
@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "Spotify (Público - Sem Premium)",
        "id": "spotify-public-addon",
        "version": "2.0.0",
        "description": "Usa token anonimo do web player do Spotify, não precisa criar app nem Premium",
        "author": "public",
        "capabilities": {"search": True, "stream": True},
        "audioQuality": "HIGH",
        "format": "AAC",
        "searchEndpoint": "/search",
        "streamEndpoint": "/stream",
        "manifestVersion": 1
    })

@app.route("/health")
def health():
    token = get_anonymous_spotify_token()
    return jsonify({"status": "ok", "token_ok": bool(token)})

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", "20")
    if not q:
        return jsonify({"tracks": [], "total": 0})

    token = get_anonymous_spotify_token()
    if not token:
        return jsonify({"tracks": [], "total": 0, "error": "Não conseguiu pegar token anonimo do Spotify"}), 500

    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": q, "type": "track", "limit": limit, "market": "BR"}
    r = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params, timeout=10)

    if r.status_code != 200:
        return jsonify({"tracks": [], "total": 0, "error": r.text}), r.status_code

    data = r.json()
    tracks = []
    for item in data.get("tracks", {}).get("items", []):
        tracks.append({
            "id": item["id"],
            "title": item["name"],
            "artist": ", ".join([a["name"] for a in item["artists"]]),
            "album": item["album"]["name"] if item.get("album") else "",
            "duration": item["duration_ms"] // 1000,
            "artwork": item["album"]["images"][0]["url"] if item["album"]["images"] else None,
            "audioQuality": "HIGH",
            "format": "AAC",
            "source": "spotify"
        })

    return jsonify({"tracks": tracks, "total": len(tracks)})

@app.route("/stream")
def stream():
    # Mesmo esquema: deixa o BitChord fazer fallback pro YouTube Music
    # que já está Always on no seu app
    return jsonify({"error": "Usa fallback YouTube Music", "fallback": True}), 404

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
