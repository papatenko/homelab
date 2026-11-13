#!/usr/bin/env python3
"""Rebuild an ordered Navidrome playlist from a CSV track list.

Re-runnable: each run replaces the playlist's contents with every track that
now matches the library, in CSV order, and rewrites the missing/ambiguous
reports. Run it again after adding music files and a library scan.

Env: ND_URL, ND_USER, ND_PASS. Standard library only.
Usage: sync_playlist.py TRACKS.csv "Playlist name" REPORT_DIR [--dry-run]
"""
import csv, difflib, hashlib, json, os, re, secrets, sys, urllib.parse, urllib.request

MATCH, AMBIGUOUS = 0.86, 0.66
VARIANT = re.compile(r"\b(remix|slowed|sped ?up|reverb|nightcore|extended|instrumental|acapella|live|edit|mix|version|vip)\b", re.I)
NOISE = re.compile(r"\((?:official|lyric|lyrics|audio|video|visualizer|hd|hq|4k|explicit)[^)]*\)|\[(?:official|lyric|lyrics|audio|video|visualizer|hd|hq|4k|explicit)[^\]]*\]|\b(?:official (?:music )?video|lyric video|official audio)\b", re.I)


def norm(s):
    s = NOISE.sub(" ", s or "").lower()
    s = re.sub(r"\b(feat|ft|featuring)\.?\b.*", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def variants(s):
    return {m.lower().replace(" ", "") for m in VARIANT.findall(s or "")}


def api(method, params=(), post=False):
    salt = secrets.token_hex(6)
    auth = [("u", os.environ["ND_USER"]), ("t", hashlib.md5((os.environ["ND_PASS"] + salt).encode()).hexdigest()),
            ("s", salt), ("v", "1.16.1"), ("c", "playlist-sync"), ("f", "json")]
    data = urllib.parse.urlencode(auth + list(params)).encode()
    url = f"{os.environ['ND_URL'].rstrip('/')}/rest/{method}"
    req = urllib.request.Request(url, data=data) if post else urllib.request.Request(f"{url}?{data.decode()}")
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)["subsonic-response"]
    if body.get("status") != "ok":
        raise SystemExit(f"{method} failed: {body.get('error')}")
    return body


def score(row, song):
    t = difflib.SequenceMatcher(None, norm(row["title"]), norm(song.get("title"))).ratio()
    a = difflib.SequenceMatcher(None, norm(row["artist"]), norm(song.get("artist"))).ratio()
    s = 0.75 * t + 0.25 * a
    if variants(row["title"]) != variants(song.get("title")):
        s -= 0.2  # a remix/slowed edit is a different recording
    return s


def best(row):
    q = norm(row["title"]) or row["title"]
    songs = api("search3", [("query", q), ("songCount", 25), ("artistCount", 0), ("albumCount", 0)]).get("searchResult3", {}).get("song", [])
    ranked = sorted(((score(row, s), s) for s in songs), key=lambda x: -x[0])
    return ranked[0] if ranked else (0.0, None)


def links(row):
    q = urllib.parse.quote_plus(f"{row['artist']} {row['title']}")
    return (f"[Bandcamp](https://bandcamp.com/search?q={q}) · [Qobuz](https://www.qobuz.com/us-en/search?q={q}) · "
            f"[Traxsource](https://www.traxsource.com/search?term={q}) · [source](https://music.youtube.com/watch?v={row['youtube_id']})")


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    csv_path, name, out = args
    os.makedirs(out, exist_ok=True)
    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    matched, missing, ambiguous, ids = [], [], [], []
    for row in rows:
        s, song = best(row)
        if song and s >= MATCH:
            if song["id"] not in ids:  # Navidrome keeps duplicates; avoid accidental double adds
                ids.append(song["id"])
            matched.append({**row, "score": f"{s:.2f}", "song_id": song["id"], "lib_artist": song.get("artist"), "lib_title": song.get("title")})
        elif song and s >= AMBIGUOUS:
            ambiguous.append({**row, "score": f"{s:.2f}", "song_id": song["id"], "lib_artist": song.get("artist"), "lib_title": song.get("title")})
        else:
            missing.append(row)
    if not dry:
        existing = [p for p in api("getPlaylists").get("playlists", {}).get("playlist", []) if p["name"] == name]
        params = [("songId", i) for i in ids]
        params = ([("playlistId", existing[0]["id"])] if existing else [("name", name)]) + params
        api("createPlaylist", params, post=True)  # with playlistId this replaces the contents
    for fname, data in (("matched.csv", matched), ("ambiguous.csv", ambiguous), ("missing.csv", missing)):
        with open(os.path.join(out, fname), "w", newline="", encoding="utf-8") as f:
            if data:
                w = csv.DictWriter(f, fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
    with open(os.path.join(out, "missing.md"), "w", encoding="utf-8") as f:
        f.write(f"# {name}: tracks not in the library\n\n{len(rows)} total · {len(matched)} matched · {len(ambiguous)} ambiguous · {len(missing)} missing\n\n")
        f.write("| # | Artist | Title | Find it |\n|---|---|---|---|\n")
        for r in ambiguous + missing:
            flag = " (possible match: review)" if r in ambiguous else ""
            f.write(f"| {r['position']} | {r['artist'].replace('|', '/')} | {r['title'].replace('|', '/')}{flag} | {links(r)} |\n")
    print(json.dumps({"total": len(rows), "matched": len(matched), "unique_in_playlist": len(ids),
                      "ambiguous": len(ambiguous), "missing": len(missing), "dry_run": dry}))


if __name__ == "__main__":
    main()
