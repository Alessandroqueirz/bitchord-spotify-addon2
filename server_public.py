from flask import Flask, jsonify, request, send_file
import requests
import re
import time
import os

app = Flask(__name__)

# Cache do token anonimo Spotify
_cached_token = {"token": None, "expires_at": 0}

def get_anonymous_spotify_token():
    global _cached_token
    now = time.time()
    if _cached_token["token"] and now < _cached_token["expires_at"] - 60:
        return _cached_token["token"]
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "text/html"}
        r = requests.get("https://open.spotify.com/search", headers=headers, timeout=10)
        m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', r.text)
        if m:
            token = m.group(1)
            _cached_token["token"] = token
            _cached_token["expires_at"] = now + 3600
            return token
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
def index():
    base_url = request.host_url.rstrip("/")
    return f"""
    <html><head><title>BitChord Addons - Spotify + Apple Music</title></head>
    <body style="background:#121212;color:white;font-family:sans-serif;padding:20px">
    <h1>🎵 BitChord Addons</h1>
    <p>Você tem 2 addons disponíveis:</p>
    <ul>
      <li><b>Spotify:</b> <a href="{base_url}/spotify/manifest.json" style="color:#1DB954">{base_url}/spotify/manifest.json</a></li>
      <li><b>Apple Music:</b> <a href="{base_url}/apple/manifest.json" style="color:#FA243C">{base_url}/apple/manifest.json</a></li>
    </ul>
    <p>Cole cada link no BitChord em Sources > Add an addon</p>
    </body></html>
    """

# ========== SPOTIFY ==========
@app.route("/spotify/manifest.json")
@app.route("/manifest.json")
def manifest_spotify():
    base_url = request.host_url.rstrip("/")
    icon_url = f"{base_url}/spotify/icon.png"
    return jsonify({
        "name": "Spotify",
        "id": "spotify-public-addon",
        "version": "2.3.0",
        "description": "Spotify publico - token anonimo, sem Premium",
        "author": "public",
        "capabilities": {"search": True, "stream": True},
        "audioQuality": "HIGH",
        "format": "AAC",
        "searchEndpoint": "/spotify/search",
        "streamEndpoint": "/spotify/stream",
        "manifestVersion": 1,
        "icon": icon_url, "logo": icon_url, "image": icon_url, "artwork": icon_url,
        "color": "#1DB954", "backgroundColor": "#121212"
    })

@app.route("/spotify/icon.png")
@app.route("/icon.png")
def serve_spotify_icon():
    for fname in ["icon.png", "spotify_icon.png"]:
        p = os.path.join(os.path.dirname(__file__), fname)
        if os.path.exists(p):
            return send_file(p, mimetype="image/png")
    return "", 404

@app.route("/spotify/search")
@app.route("/search")
def search_spotify():
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", "20")
    if not q:
        return jsonify({"tracks": [], "total": 0})
    token = get_anonymous_spotify_token()
    if not token:
        return jsonify({"tracks": [], "total": 0, "error": "token anonimo falhou"}), 500
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
            "audioQuality": "HIGH", "format": "AAC", "source": "spotify"
        })
    return jsonify({"tracks": tracks, "total": len(tracks)})

@app.route("/spotify/stream")
@app.route("/stream")
def stream_spotify():
    return jsonify({"error": "Usa fallback YouTube Music", "fallback": True}), 404

# ========== APPLE MUSIC ==========
@app.route("/apple/manifest.json")
def manifest_apple():
    base_url = request.host_url.rstrip("/")
    icon_url = f"{base_url}/apple/icon.png"
    return jsonify({
        "name": "Apple Music",
        "id": "apple-music-addon",
        "version": "1.0.0",
        "description": "Apple Music publico via iTunes Search - sem conta",
        "author": "public",
        "capabilities": {"search": True, "stream": True},
        "audioQuality": "HIGH", "format": "AAC",
        "searchEndpoint": "/apple/search",
        "streamEndpoint": "/apple/stream",
        "manifestVersion": 1,
        "icon": icon_url, "logo": icon_url, "image": icon_url, "artwork": icon_url,
        "color": "#FA243C", "backgroundColor": "#000000"
    })

@app.route("/apple/icon.png")
def serve_apple_icon():
    for fname in ["apple_icon.png", "icon_apple.png"]:
        p = os.path.join(os.path.dirname(__file__), fname)
        if os.path.exists(p):
            return send_file(p, mimetype="image/png")
    # fallback spotify icon
    p = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(p):
        return send_file(p, mimetype="image/png")
    return "", 404

@app.route("/apple/search")
def search_apple():
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", "20")
    if not q:
        return jsonify({"tracks": [], "total": 0})
    try:
        limit_int = int(limit)
    except:
        limit_int = 20
    limit_int = min(max(limit_int, 1), 50)
    params = {"term": q, "media": "music", "entity": "song", "limit": limit_int, "country": "BR"}
    try:
        r = requests.get("https://itunes.apple.com/search", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return jsonify({"tracks": [], "total": 0, "error": str(e)}), 500
    tracks = []
    for item in data.get("results", []):
        artwork = item.get("artworkUrl100")
        if artwork:
            artwork = artwork.replace("100x100bb", "600x600bb").replace("100x100", "600x600")
        duration = (item.get("trackTimeMillis", 0) // 1000) if item.get("trackTimeMillis") else 0
        tracks.append({
            "id": str(item.get("trackId", "")),
            "title": item.get("trackName", ""),
            "artist": item.get("artistName", ""),
            "album": item.get("collectionName", ""),
            "duration": duration,
            "artwork": artwork,
            "audioQuality": "HIGH", "format": "AAC", "source": "apple_music"
        })
    return jsonify({"tracks": tracks, "total": len(tracks)})

@app.route("/apple/stream")
def stream_apple():
    return jsonify({"error": "Usa fallback YouTube Music", "fallback": True}), 404

@app.route("/health")
def health():
    # Health leve e instantaneo para UptimeRobot nao dar Down
    return jsonify({"status": "ok", "spotify": "ok", "apple": "ok"})

@app.route("/health/detailed")
def health_detailed():
    token = get_anonymous_spotify_token()
    return jsonify({"status": "ok", "spotify_token_ok": bool(token), "apple": "ok"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
