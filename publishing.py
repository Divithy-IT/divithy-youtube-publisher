"""One reviewed workflow for both interfaces; planning is offline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from local_state import save_state
from planner import build_queue, discover_packages, queue_as_json


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    for name in ("content_root", "client_secret"):
        value = Path(config.get(name, "")).expanduser()
        config[name] = str((path.parent / value).resolve())
    return config


def publishing_options(config: dict) -> dict:
    defaults = {
        "notify_main": True, "notify_shorts": False, "made_for_kids": False,
        "schedule_publication": False, "category_id": "20", "default_language": "pl",
        "playlist_names": "", "playlist_privacy": "private", "expected_channel_id": "",
    }
    result = {name: config.get(name, value) for name, value in defaults.items()}
    for name in ("notify_main", "notify_shorts", "made_for_kids", "schedule_publication"):
        if type(result[name]) is not bool:
            raise ValueError(f"{name} must be a JSON boolean (true or false).")
    if result["playlist_privacy"] not in ("private", "unlisted", "public"):
        raise ValueError("playlist_privacy must be private, unlisted or public.")
    return result


def _row(item) -> dict:
    row = json.loads(queue_as_json([item]))[0]
    row["thumbnail_sha256"] = hashlib.sha256(item.thumbnail.read_bytes()).hexdigest() if item.thumbnail else None
    return row


def _content(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in ("publish_at_local", "publish_at_utc")}


def prepare(config: dict, state: dict, limit: int = 0) -> tuple[list, dict, str]:
    if limit < 0:
        raise ValueError("Upload limit must be zero or positive.")
    if state.get("inflight"):
        raise ValueError("An earlier upload has an unknown outcome. Reconcile state.inflight with YouTube Studio before retrying; see docs/QUICKSTART_EN.md.")
    content_root = str(Path(config["content_root"]).expanduser().resolve())
    if state.get("content_root", content_root) != content_root:
        raise ValueError("Content root changed. Reconcile moved files with existing YouTube IDs before continuing.")
    if state["uploads"] and not state.get("content_root"):
        old_roots = {str(Path(record["video"]).parent.parent) for record in state["uploads"].values() if record.get("video")}
        if old_roots and old_roots != {content_root}:
            raise ValueError("Legacy upload paths differ from content_root. Reconcile existing YouTube IDs first.")
    packages = discover_packages(Path(config["content_root"]))
    games = [part.strip() for part in config.get("game_order", "L4D2,PUBG").split(",") if part.strip()]
    types = [part.strip() for part in config.get("type_order", "kompilacja,pelna_rozgrywka").split(",") if part.strip()]
    start = date.fromisoformat(config["start_date"])
    zone = config.get("timezone", "Europe/Warsaw")
    original = build_queue(packages, start, zone, games, types)
    reserved = state.get("plan", {})
    uploads = state["uploads"]
    old_paths = {entry.get("video"): key for key, entry in {**uploads, **reserved}.items()}
    for item in original:
        old_key = old_paths.get(str(item.video))
        if old_key and old_key != item.key:
            raise ValueError(f"Previously planned file changed: {item.video}. Reconcile its YouTube ID first.")
    known_packages = {item.package.folder for item in original if item.key in reserved or item.key in uploads}
    if not reserved and not uploads:
        items = original
    else:
        items = []
        for package in packages:
            if package.folder not in known_packages:
                continue
            group = [item for item in original if item.package.folder == package.folder]
            offsets = {
                datetime.fromisoformat(uploads[item.key]["publish_at"]) - item.publish_at
                for item in group if item.key in uploads and uploads[item.key].get("publish_at")
            }
            if not any(item.key in reserved for item in group) and len(offsets) > 1:
                raise ValueError("Legacy package has inconsistent dates; reconcile its schedule manually.")
            offset = next(iter(offsets), timedelta())
            for item in group:
                previous = reserved.get(item.key)
                if previous:
                    if _content(previous) != _content(_row(item)):
                        raise ValueError(f"Previously approved metadata or asset changed: {item.video}")
                    item = replace(item, publish_at=datetime.fromisoformat(previous["publish_at_local"]))
                else:
                    item = replace(item, publish_at=item.publish_at + offset)
                items.append(item)
        previous_dates = [datetime.fromisoformat(row["publish_at_local"]) for row in reserved.values()]
        previous_dates += [datetime.fromisoformat(row["publish_at"]) for row in uploads.values() if row.get("publish_at")]
        previous_dates += [item.publish_at for item in items]
        resume = max(start, max(previous_dates).astimezone(ZoneInfo(zone)).date() + timedelta(days=1)) if previous_dates else start
        items += build_queue([package for package in packages if package.folder not in known_packages], resume, zone, games, types)
        items.sort(key=lambda item: item.publish_at)
    pending = [item for item in items if item.key not in uploads]
    selected = pending[:limit] if limit else pending
    repairs = [
        {"key": item.key, "video_id": uploads[item.key]["video_id"],
         "thumbnail": bool(item.thumbnail and not uploads[item.key].get("thumbnail_set", False)),
         "playlist": item.kind == "film" and not uploads[item.key].get("playlist_added", False)}
        for item in items if item.key in uploads and (
            (item.thumbnail and not uploads[item.key].get("thumbnail_set", False)) or
            (item.kind == "film" and not uploads[item.key].get("playlist_added", False))
        )
    ]
    payload = {"options": publishing_options(config), "items": [_row(item) for item in items],
               "selected_keys": [item.key for item in selected], "repairs": repairs}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    payload["approval_sha256"] = digest
    payload["new_upload_count"] = len(selected)
    return items, payload, digest


def publish(youtube, config: dict, state: dict, state_path: Path, items: list,
            plan: dict, progress=print) -> None:
    # Caller holds state_lock from reading state through completion.
    from youtube_api import add_to_playlist, connected_channel, ensure_playlist, set_thumbnail, upload_video

    options = publishing_options(config)
    expected = options["expected_channel_id"]
    if not expected:
        raise ValueError("Set expected_channel_id using --check-channel before uploading.")
    channel = connected_channel(youtube)
    if channel["id"] != expected or state.get("channel_id", expected) != expected:
        raise ValueError("Connected YouTube channel does not match configuration or upload history.")
    selected = set(plan["selected_keys"])
    now = datetime.now(timezone.utc)
    if options["schedule_publication"] and any(item.key in selected and item.publish_at <= now for item in items):
        raise ValueError("A selected publication date is in the past. Review a future plan before uploading.")
    state["channel_id"] = expected
    state["content_root"] = str(Path(config["content_root"]).expanduser().resolve())
    state.setdefault("plan", {}).update({row["key"]: row for row in plan["items"]})
    save_state(state_path, state)
    playlists = {}
    for entry in options["playlist_names"].split(";"):
        game, separator, title = entry.partition("=")
        if separator and game.strip() and title.strip():
            playlists[game.strip()] = title.strip()
    playlist_cache = {}
    planned_rows = {row["key"]: row for row in plan["items"]}
    for item in items:
        key = item.key
        existing = state["uploads"].get(key)
        if not existing and key not in selected:
            continue
        if planned_rows.get(key) != _row(item):
            raise ValueError(f"An asset changed after review: {item.video}")
        if not existing:
            # Persist intent before videos.insert; an unknown result blocks retries.
            state["inflight"] = {"key": key, "video": str(item.video),
                                 "title": item.metadata.title, "publish_at": item.publish_at.isoformat(),
                                 "scheduled": options["schedule_publication"]}
            save_state(state_path, state)
            video_id = upload_video(
                youtube, item, options["notify_main"] if item.kind == "film" else options["notify_shorts"],
                str(options["category_id"]), options["made_for_kids"], options["schedule_publication"],
                progress, options["default_language"],
            )
            existing = {**state["inflight"], "video_id": video_id,
                        "thumbnail_set": item.thumbnail is None, "playlist_added": item.kind != "film"}
            state["uploads"][key] = existing
            state.pop("inflight")
            save_state(state_path, state)
            progress(f"Uploaded {item.video.name}: {video_id}")
        if item.thumbnail and not existing.get("thumbnail_set", False):
            set_thumbnail(youtube, existing["video_id"], item.thumbnail)
            existing["thumbnail_set"] = True
            save_state(state_path, state)
        if item.kind == "film" and not existing.get("playlist_added", False):
            title = playlists.get(item.package.game, item.package.game)
            playlist_id = playlist_cache.get(title)
            if not playlist_id:
                playlist_id = ensure_playlist(youtube, title, options["playlist_privacy"], options["default_language"])
                playlist_cache[title] = playlist_id
            add_to_playlist(youtube, playlist_id, existing["video_id"])
            existing.update(playlist_added=True, playlist_id=playlist_id)
            save_state(state_path, state)
