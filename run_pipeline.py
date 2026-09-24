"""Run this. Pulls new clips, processes them, writes to output/.

Safe to run repeatedly (e.g. on a schedule) - already-processed clips
are tracked in state.json and skipped.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from fetch_clips import get_app_token, get_broadcaster_id, list_clips, download_clip
from process_clip import process

load_dotenv()

RAW_DIR = Path("raw")
OUTPUT_DIR = Path("output")
STATE_PATH = Path("state.json")


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"processed_clip_ids": []}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def main() -> None:
    client_id = os.environ["TWITCH_CLIENT_ID"]
    client_secret = os.environ["TWITCH_CLIENT_SECRET"]
    streamer_login = os.environ["STREAMER_LOGIN"]
    fetch_limit = int(os.environ.get("CLIP_FETCH_LIMIT", "20"))

    RAW_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    state = load_state()
    processed_ids = set(state["processed_clip_ids"])

    print("Authenticating with Twitch...")
    token = get_app_token(client_id, client_secret)
    broadcaster_id = get_broadcaster_id(streamer_login, client_id, token)

    print(f"Fetching clips for {streamer_login}...")
    clips = list_clips(broadcaster_id, client_id, token, limit=fetch_limit)
    new_clips = [c for c in clips if c["id"] not in processed_ids]

    if not new_clips:
        print("No new clips since last run.")
        return

    print(f"Found {len(new_clips)} new clip(s).")

    for clip in new_clips:
        clip_id = clip["id"]
        title = clip["title"]
        safe_name = "".join(ch if ch.isalnum() or ch in " -_" else "" for ch in title)[:60].strip()
        raw_path = RAW_DIR / f"{clip_id}.mp4"
        output_path = OUTPUT_DIR / f"{clip_id}.mp4"
        try:
            print(f"  Downloading: {title}")
            download_clip(clip["url"], str(raw_path))

            print("  Processing (vertical + captions)...")
            process(str(raw_path), str(output_path))

            print(f"  Done -> {output_path}")
            processed_ids.add(clip_id)
        except Exception as e:
            print(f"  Failed on clip {clip_id} ({title}): {e}")
            continue

    state["processed_clip_ids"] = list(processed_ids)
    save_state(state)

    print(f"\n{len(new_clips)} clip(s) ready in {OUTPUT_DIR}/")
    print("Add them to your Clip Queue dashboard with the campaign's required credit tag, then post.")


if __name__ == "__main__":
    main()
