"""Non-interactive publisher used after reviewing the generated queue."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from planner import build_queue, discover_packages
from youtube_api import (
    add_to_playlist,
    authenticate,
    ensure_playlist,
    load_state,
    save_state,
    set_thumbnail,
    upload_video,
)


APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "publisher_config.json"
TOKEN_FILE = APP_DIR / "token.json"
STATE_FILE = APP_DIR / "upload_state.json"


def playlist_mapping(value: str) -> dict[str, str]:
    result = {}
    for entry in value.split(";"):
        game, separator, title = entry.partition("=")
        if separator and game.strip() and title.strip():
            result[game.strip()] = title.strip()
    return result


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Maximum new uploads; 0 means all")
    parser.add_argument("--inspect-only", action="store_true")
    args = parser.parse_args()

    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    config.setdefault("type_order", "kompilacja,pelna_rozgrywka")
    config.setdefault("playlist_names", "L4D2=Left 4 Dead 2;PUBG=PUBG;CS2=Counter-Strike 2")
    packages = discover_packages(Path(config["content_root"]))
    state = load_state(STATE_FILE)
    game_order = [
        part.strip()
        for part in config.get("game_order", "L4D2,PUBG").split(",")
        if part.strip()
    ]
    type_order = [
        part.strip()
        for part in config.get("type_order", "kompilacja,pelna_rozgrywka").split(",")
        if part.strip()
    ]

    # Build the original queue once to obtain stable item keys and to repair
    # thumbnails/playlists for uploads completed during an earlier run.
    all_items = build_queue(
        packages,
        date.fromisoformat(config["start_date"]),
        config.get("timezone", "Europe/Warsaw"),
        game_order,
        type_order,
    )

    pending_folders = {
        item.package.folder
        for item in all_items
        if item.key not in state["uploads"]
    }
    pending_packages = [
        package for package in packages if package.folder in pending_folders
    ]

    resume_date = date.fromisoformat(config["start_date"])
    completed_dates = []
    for uploaded in state["uploads"].values():
        value = uploaded.get("publish_at")
        if value:
            completed_dates.append(datetime.fromisoformat(value).date())
    if completed_dates:
        resume_date = max(resume_date, max(completed_dates) + timedelta(days=1))

    # New games must start after the last already scheduled upload. Rebuilding
    # only the pending packages prevents newly added series from occupying
    # dates that are already taken by older uploads.
    items = build_queue(
        pending_packages,
        resume_date,
        config.get("timezone", "Europe/Warsaw"),
        game_order,
        type_order,
    )
    pending = [item for item in items if item.key not in state["uploads"]]
    if args.inspect_only:
        for item in pending:
            print(item.publish_at.isoformat(), item.video.name, item.metadata.title)
        return
    if args.limit:
        pending = pending[: args.limit]
    youtube = authenticate(Path(config["client_secret"]), TOKEN_FILE)
    playlists = playlist_mapping(config.get("playlist_names", ""))
    playlist_cache: dict[str, str] = {}
    # Repair supplementary steps after an interrupted run without uploading
    # the large video again.
    for item in all_items:
        existing = state["uploads"].get(item.key)
        if not existing:
            continue
        if item.thumbnail and not existing.get("thumbnail_set", False):
            set_thumbnail(youtube, existing["video_id"], item.thumbnail)
            existing["thumbnail_set"] = True
            save_state(STATE_FILE, state)
        if item.kind == "film" and not existing.get("playlist_added", False):
            title = playlists.get(item.package.game, item.package.game)
            playlist_id = playlist_cache.get(title)
            if not playlist_id:
                playlist_id = ensure_playlist(youtube, title)
                playlist_cache[title] = playlist_id
            add_to_playlist(youtube, playlist_id, existing["video_id"])
            existing["playlist_added"] = True
            existing["playlist_id"] = playlist_id
            save_state(STATE_FILE, state)
    if not pending:
        print("Nothing to upload; supplementary steps are complete.")
        return
    for position, item in enumerate(pending, start=1):
        print(f"[{position}/{len(pending)}] Uploading {item.video.name}", flush=True)
        video_id = upload_video(
            youtube,
            item,
            config.get("notify_main", True) if item.kind == "film" else config.get("notify_shorts", False),
            config.get("category_id", "20"),
            config.get("made_for_kids", False),
            True,
            lambda message: print(message, flush=True),
        )
        state["uploads"][item.key] = {
            "video_id": video_id,
            "video": str(item.video),
            "publish_at": item.publish_at.isoformat(),
            "scheduled": True,
            "thumbnail_set": item.thumbnail is None,
            "playlist_added": item.kind != "film",
        }
        save_state(STATE_FILE, state)
        if item.thumbnail:
            set_thumbnail(youtube, video_id, item.thumbnail)
            state["uploads"][item.key]["thumbnail_set"] = True
            save_state(STATE_FILE, state)
        if item.kind == "film":
            title = playlists.get(item.package.game, item.package.game)
            playlist_id = playlist_cache.get(title)
            if not playlist_id:
                playlist_id = ensure_playlist(youtube, title)
                playlist_cache[title] = playlist_id
            add_to_playlist(youtube, playlist_id, video_id)
            state["uploads"][item.key]["playlist_added"] = True
            state["uploads"][item.key]["playlist_id"] = playlist_id
            save_state(STATE_FILE, state)
        status = youtube.videos().list(part="snippet,status,processingDetails", id=video_id).execute()["items"][0]
        print(
            json.dumps(
                {
                    "video_id": video_id,
                    "title": status["snippet"]["title"],
                    "privacyStatus": status["status"].get("privacyStatus"),
                    "publishAt": status["status"].get("publishAt"),
                    "uploadStatus": status["status"].get("uploadStatus"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
