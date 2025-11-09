import os
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=client_id,
    client_secret=client_secret
))

def build_song_list(playlist_url, output_file="songs.json", limit=100):
    results = sp.playlist_items(playlist_url, additional_types=["track"], limit=limit)
    tracks = []

    for item in results["items"]:
        track = item["track"]
        if not track or not track["preview_url"]:
            continue  # skip if no preview available

        title = track["name"]
        artist = track["artists"][0]["name"]
        preview = track["preview_url"]

        tracks.append({
            "artist": artist,
            "title": title,
            "preview_url": preview,
            "answer": title
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(tracks, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(tracks)} songs to {output_file}")

# Example usage:
# build_song_list("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")
