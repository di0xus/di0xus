#!/usr/bin/env python3
"""
Updates README.md with weekly top artists from ListenBrainz.
Replaces the static top artists table in the README.
"""

import os
import re
import json
import urllib.request
from datetime import datetime

LB_USER = os.environ.get("LB_USER", "dioxin")
LB_API = f"https://api.listenbrainz.org/1/user/{LB_USER}/listens"
TOP_ARTISTS_API = f"https://api.listenbrainz.org/1/stats/user/{LB_USER}/top-artists"

README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")

# ─── Fetch last 25 listens and tally artist plays ───────────────────────────

def get_top_artists(limit=5):
    """Fetch recent listens and compute top artists manually since stats endpoint is unreliable."""
    url = f"{LB_API}?limit=50"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"ListenBrainz API error: {e}")
        return None

    listens = data.get("payload", {}).get("listens", [])
    if not listens:
        return None

    artist_counts = {}
    for listen in listens:
        meta = listen.get("track_metadata", {})
        artist = meta.get("artist_name")
        if artist:
            artist_counts[artist] = artist_counts.get(artist, 0) + 1

    sorted_artists = sorted(artist_counts.items(), key=lambda x: -x[1])
    return sorted_artists[:limit]

# ─── Fetch now playing ───────────────────────────────────────────────────────

def get_now_playing():
    url = f"https://api.listenbrainz.org/1/user/{LB_USER}/playing-now"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"Playing-now error: {e}")
        return None

    listens = data.get("payload", {}).get("listens", [])
    if not listens:
        return None

    meta = listens[0].get("track_metadata", {})
    track = meta.get("track_name", "Unknown")
    artist = meta.get("artist_name", "Unknown")
    release = meta.get("release_name", "")

    return {"track": track, "artist": artist, "release": release}

# ─── Build the artists table markdown ───────────────────────────────────────

def build_artists_md(artists):
    lines = ["| # | Artist | Plays |", "|---|--------|-------|"]
    for i, (name, count) in enumerate(artists, 1):
        lines.append(f"| {i} | **{name}** | {count} |")
    return "\n".join(lines)

# ─── Build now-playing badge ─────────────────────────────────────────────────

def build_now_playing_md(np_info):
    if not np_info:
        return (
            "[![Now Playing](https://img.shields.io/badge/Now%20Playing-nothing%20playing-1DB954?"
            "style=for-the-badge&logo=listenbrainz&logoColor=1DB954)]"
            "(https://listenbrainz.org/user/dioxin)"
        )
    # URL-encode the track/artist for the badge label
    label = f"Now Playing-{np_info['artist']}–{np_info['track']}"
    label_encoded = label.replace(" ", "%20")
    return (
        f"[![Now Playing](https://img.shields.io/badge/{label_encoded}-1DB954"
        f"?style=for-the-badge&logo=listenbrainz&logoColor=1DB954)]"
        f"(https://listenbrainz.org/user/dioxin)"
        f"\n> **{np_info['track']}** — *{np_info['release']}*"
    )

# ─── Patch README sections in-place ─────────────────────────────────────────

def update_readme(top_artists, now_playing):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace NOW PLAYING section
    np_section = build_now_playing_section(now_playing)
    content = re.sub(
        r"(?s)<!--\s*NOW_PLAYING_START\s*-->.*?<!--\s*NOW_PLAYING_END\s*-->",
        np_section,
        content,
    )

    # Replace TOP ARTISTS section
    artists_md = build_artists_md(top_artists)
    artists_section = (
        f'<!-- TOP_ARTISTS_START -->\n{artists_md}\n<!-- TOP_ARTISTS_END -->'
    )
    content = re.sub(
        r"(?s)<!--\s*TOP_ARTISTS_START\s*-->.*?<!--\s*TOP_ARTISTS_END\s*-->",
        artists_section,
        content,
    )

    # Update last-updated timestamp
    content = re.sub(
        r"(\*\*Last updated:)\*\* .*",
        f"**Last updated:** {datetime.now().strftime('%Y-%m-%d')}",
        content,
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"README updated at {datetime.now()}")


def build_now_playing_section(np_info):
    if not np_info:
        badge = (
            "https://img.shields.io/badge/Now%20Playing-nothing%20playing"
            "-1DB954?style=for-the-badge&logo=listenbrainz&logoColor=1DB954"
        )
        link = "(https://listenbrainz.org/user/dioxin)"
        return f"""<!-- NOW_PLAYING_START -->
[![Now Playing]({badge}]){link}

> No recent scrobbles found.
<!-- NOW_PLAYING_END -->"""

    # Build badge URL-safe label: "Artist – Track"
    raw = f"Now Playing-{np_info['artist']}–{np_info['track']}"
    label = urllib.parse.quote(raw, safe="")

    badge = (
        f"https://img.shields.io/badge/{label}"
        f"-1DB954?style=for-the-badge&logo=listenbrainz&logoColor=1DB954"
    )
    link = "(https://listenbrainz.org/user/dioxin)"
    release = np_info.get("release", "")
    return f"""<!-- NOW_PLAYING_START -->
[![Now Playing]({badge}]){link}

> **{np_info['track']}** — *{release}*
<!-- NOW_PLAYING_END -->"""


if __name__ == "__main__":
    import urllib.parse  # lazy import

    top_artists = get_top_artists(limit=5)
    now_playing = get_now_playing()

    if top_artists is None:
        print("Failed to fetch top artists, aborting.")
        exit(1)

    update_readme(top_artists, now_playing)
