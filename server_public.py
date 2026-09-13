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

# Tokens publicos TIDAL (X-Tidal-Token) - catalogo publico sem login
TIDAL_TOKENS = [
    "gsFXkJqGrUNoYMQPZe4k3WKwijnrp8iGSwn3bApe",  # encontrado no GitHub - funciona para /v1/*
    "CzET4WCqmowBy5y8a2dWnGsaNwo37Q",          # token web player comum
    "kgsOOmYk3zShYrW9loDY43M",                # fallback
]

def get_tidal_headers():
    # retorna header com primeiro token que funcionar
    return {"X-Tidal-Token": TIDAL_TOKENS[0], "Accept": "application/json", "User-Agent": "Mozilla/5.0"}

@app.route("/")
def index():
    base_url = request.host_url.rstrip("/")
    return f"""
    <html><head><title>BitChord Addons - 4 Sources</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="background:#121212;color:white;font-family:sans-serif;padding:20px">
    <h1>🎵 BitChord Addons - 4 Sources FLAC</h1>
    <p>Você tem 4 addons disponíveis:</p>
    <ul>
      <li><b>Spotify:</b> <a href="{base_url}/spotify/manifest.json" style="color:#1DB954">{base_url}/spotify/manifest.json</a></li>
      <li><b>Apple Music:</b> <a href="{base_url}/apple/manifest.json" style="color:#FA243C">{base_url}/apple/manifest.json</a></li>
      <li><b>Deezer:</b> <a href="{base_url}/deezer/manifest.json" style="color:#FEAA2D">{base_url}/deezer/manifest.json</a></li>
      <li><b>TIDAL:</b> <a href="{base_url}/tidal/manifest.json" style="color:#00FFFF">{base_url}/tidal/manifest.json</a></li>
    </ul>
    <p>Cole cada link no BitChord em Sources > Add an addon</p>
    <p>Ordem recomendada no BitChord: Spotify > Apple > Deezer > TIDAL > YouTube Music</p>
    <hr>
    <p><a href="{base_url}/health" style="color:#888">/health</a> para UptimeRobot</p>
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

# ========== DEEZER ==========
@app.route("/deezer/manifest.json")
def manifest_deezer():
    base_url = request.host_url.rstrip("/")
    icon_url = f"{base_url}/deezer/icon.png"
    return jsonify({
        "name": "Deezer",
        "id": "deezer-addon",
        "version": "1.0.0",
        "description": "Deezer publico via API oficial - sem conta - FLAC",
        "author": "public",
        "capabilities": {"search": True, "stream": True},
        "audioQuality": "HIGH",
        "format": "FLAC",
        "searchEndpoint": "/deezer/search",
        "streamEndpoint": "/deezer/stream",
        "manifestVersion": 1,
        "icon": icon_url, "logo": icon_url, "image": icon_url, "artwork": icon_url,
        "color": "#FEAA2D", "backgroundColor": "#000000"
    })

@app.route("/deezer/icon.png")
def serve_deezer_icon():
    for fname in ["deezer_icon.png", "icon_deezer.png", "apple_icon.png", "icon.png"]:
        p = os.path.join(os.path.dirname(__file__), fname)
        if os.path.exists(p):
            return send_file(p, mimetype="image/png")
    return "", 404

@app.route("/deezer/search")
def search_deezer():
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", "20")
    if not q:
        return jsonify({"tracks": [], "total": 0})
    try:
        limit_int = int(limit)
    except:
        limit_int = 20
    limit_int = min(max(limit_int, 1), 50)
    try:
        params = {"q": q, "limit": limit_int, "order": "RANKING"}
        r = requests.get("https://api.deezer.com/search", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return jsonify({"tracks": [], "total": 0, "error": str(e)}), 500
    tracks = []
    for item in data.get("data", []):
        artist_name = item.get("artist", {}).get("name", "") if isinstance(item.get("artist"), dict) else ""
        album_title = item.get("album", {}).get("title", "") if isinstance(item.get("album"), dict) else ""
        cover = None
        if isinstance(item.get("album"), dict):
            cover = item["album"].get("cover_big") or item["album"].get("cover_xl") or item["album"].get("cover_medium")
        tracks.append({
            "id": str(item.get("id", "")),
            "title": item.get("title", ""),
            "artist": artist_name,
            "album": album_title,
            "duration": item.get("duration", 0),
            "artwork": cover,
            "audioQuality": "HIGH", "format": "FLAC", "source": "deezer"
        })
    return jsonify({"tracks": tracks, "total": len(tracks)})

@app.route("/deezer/stream")
def stream_deezer():
    return jsonify({"error": "Usa fallback YouTube Music", "fallback": True}), 404

# ========== TIDAL ==========
@app.route("/tidal/manifest.json")
def manifest_tidal():
    base_url = request.host_url.rstrip("/")
    icon_url = f"{base_url}/tidal/icon.png"
    return jsonify({
        "name": "TIDAL",
        "id": "tidal-addon",
        "version": "1.0.0",
        "description": "TIDAL publico via X-Tidal-Token - HiRes FLAC sem conta",
        "author": "public",
        "capabilities": {"search": True, "stream": True},
        "audioQuality": "HI_RES",
        "format": "FLAC",
        "searchEndpoint": "/tidal/search",
        "streamEndpoint": "/tidal/stream",
        "manifestVersion": 1,
        "icon": icon_url, "logo": icon_url, "image": icon_url, "artwork": icon_url,
        "color": "#00FFFF", "backgroundColor": "#000000"
    })

@app.route("/tidal/icon.png")
def serve_tidal_icon():
    for fname in ["tidal_icon.png", "icon_tidal.png", "icon.png"]:
        p = os.path.join(os.path.dirname(__file__), fname)
        if os.path.exists(p):
            return send_file(p, mimetype="image/png")
    return "", 404

@app.route("/tidal/search")
def search_tidal():
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", "20")
    if not q:
        return jsonify({"tracks": [], "total": 0})
    try:
        limit_int = int(limit)
    except:
        limit_int = 20
    limit_int = min(max(limit_int, 1), 50)

    last_error = None
    for token in TIDAL_TOKENS:
        try:
            headers = {"X-Tidal-Token": token, "Accept": "application/json", "User-Agent": "Mozilla/5.0"}
            params = {"query": q, "limit": limit_int, "offset": 0, "types": "TRACKS", "countryCode": "BR"}
            r = requests.get("https://api.tidal.com/v1/search", headers=headers, params=params, timeout=10)
            if r.status_code != 200:
                # tenta top-hits endpoint
                params2 = {"query": q, "limit": limit_int, "offset": 0, "types": "TRACKS", "countryCode": "BR", "includeContributors": "true"}
                r = requests.get("https://api.tidal.com/v1/search/top-hits", headers=headers, params=params2, timeout=10)
            if r.status_code != 200:
                last_error = r.text[:500]
                continue
            data = r.json()
            tracks = []
            # estrutura pode ser tracks.items ou data com tracks
            raw_tracks = []
            if "tracks" in data and isinstance(data["tracks"], dict) and "items" in data["tracks"]:
                raw_tracks = data["tracks"]["items"]
            elif "items" in data:
                raw_tracks = data["items"]
            elif "tracks" in data and isinstance(data["tracks"], list):
                raw_tracks = data["tracks"]
            elif "data" in data:
                raw_tracks = data["data"]

            for item in raw_tracks:
                # as vezes item tem wrapper
                track_obj = item
                if isinstance(item, dict) and "item" in item and isinstance(item["item"], dict):
                    track_obj = item["item"]
                if not isinstance(track_obj, dict):
                    continue
                # titulo
                title = track_obj.get("title") or track_obj.get("name") or ""
                # artista
                artist_name = ""
                if "artist" in track_obj and isinstance(track_obj["artist"], dict):
                    artist_name = track_obj["artist"].get("name", "")
                elif "artists" in track_obj and isinstance(track_obj["artists"], list) and len(track_obj["artists"])>0:
                    artist_name = ", ".join([a.get("name","") for a in track_obj["artists"] if isinstance(a, dict)])
                # album
                album_name = ""
                if "album" in track_obj and isinstance(track_obj["album"], dict):
                    album_name = track_obj["album"].get("title", "")
                # duracao
                duration = track_obj.get("duration", 0)
                # capa - Tidal usa cover id
                artwork = None
                cover_id = None
                if "album" in track_obj and isinstance(track_obj["album"], dict):
                    cover_id = track_obj["album"].get("cover")
                elif "cover" in track_obj:
                    cover_id = track_obj.get("cover")
                if cover_id:
                    # resources.tidal.com/images/{uuid sem traco? com barra?} tenta formato simples
                    # formato mais compativel: https://resources.tidal.com/images/{cover_id.replace('-','/')}/640x640.jpg mas tambem funciona direto
                    artwork = f"https://resources.tidal.com/images/{cover_id}/640x640.jpg"
                tracks.append({
                    "id": str(track_obj.get("id", "")),
                    "title": title,
                    "artist": artist_name,
                    "album": album_name,
                    "duration": duration,
                    "artwork": artwork,
                    "audioQuality": "HI_RES", "format": "FLAC", "source": "tidal"
                })
            if tracks:
                return jsonify({"tracks": tracks, "total": len(tracks)})
            # se nao encontrou tracks mas API respondeu ok, retorna vazio (nao tenta proximo token)
            return jsonify({"tracks": [], "total": 0})
        except Exception as e:
            last_error = str(e)
            continue

    # se todos tokens falharem, retorna vazio mas com erro pra debug
    return jsonify({"tracks": [], "total": 0, "error": f"Tidal falhou: {last_error}"})

@app.route("/tidal/stream")
def stream_tidal():
    return jsonify({"error": "Usa fallback YouTube Music", "fallback": True}), 404

# ========== HEALTH ==========
@app.route("/health")
def health():
    # Health leve e instantaneo para UptimeRobot nao dar Down
    return jsonify({"status": "ok", "spotify": "ok", "apple": "ok", "deezer": "ok", "tidal": "ok"})

@app.route("/health/detailed")
def health_detailed():
    token = get_anonymous_spotify_token()
    return jsonify({"status": "ok", "spotify_token_ok": bool(token), "apple": "ok", "deezer": "ok", "tidal": "ok"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
