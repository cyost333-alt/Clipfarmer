"""Pulls a streamer's Twitch-generated clips via the Helix API and
downloads the video files with yt-dlp."""

import os
import subprocess
import requests

TWITCH_API = "https://api.twitch.tv/helix"
OAUTH_URL = "https://id.twitch.tv/oauth2/token"


def get_app_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(OAUTH_URL, params={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_broadcaster_id(login: str, client_id: str, token: str) -> str:
    resp = requests.get(
        f"{TWITCH_API}/users",
        headers={"Client-Id": client_id, "Authorization": f"Bearer {token}"},
        params={"login": login},
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    if not data:
        raise ValueError(f"No Twitch user found for login '{login}'")
    return data[0]["id"]


def list_clips(broadcaster_id: str, client_id: str, token: str, limit: int = 20) -> list[dict]:
    """Returns the streamer's most-viewed recent clips, newest activity first."""
    resp = requests.get(
        f"{TWITCH_API}/clips",
        headers={"Client-Id": client_id, "Authorization": f"Bearer {token}"},
        params={"broadcaster_id": broadcaster_id, "first": min(limit, 100)},
    )
    resp.raise_for_status()
    return resp.json()["data"]


def download_clip(clip_url: str, dest_path: str) -> None:
    """Downloads a Twitch clip to dest_path (mp4) using yt-dlp."""
    subprocess.run(
        ["yt-dlp", "-f", "best", "-o", dest_path, clip_url],
        check=True,
    )
