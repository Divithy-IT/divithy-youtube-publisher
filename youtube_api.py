from __future__ import annotations

import json
import random
import time
from datetime import timezone
from pathlib import Path
from typing import Callable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from planner import QueueItem


SCOPES = ["https://www.googleapis.com/auth/youtube"]
RETRIABLE_CODES = {500, 502, 503, 504}


def _execute_with_retry(request, attempts: int = 8):
    for retry in range(attempts):
        try:
            return request.execute()
        except (TimeoutError, ConnectionError):
            if retry == attempts - 1:
                raise
        except HttpError as error:
            if error.resp.status not in RETRIABLE_CODES or retry == attempts - 1:
                raise
        time.sleep(min(2**retry, 30) + random.random())


def authenticate(client_secret: Path, token_file: Path):
    credentials = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if not credentials.has_scopes(SCOPES):
            credentials = None
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
        credentials = flow.run_local_server(port=0, open_browser=True, prompt="consent")
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def upload_video(
    youtube,
    item: QueueItem,
    notify_subscribers: bool,
    category_id: str,
    made_for_kids: bool,
    schedule_publication: bool,
    progress: Callable[[str], None],
) -> str:
    body = {
        "snippet": {
            "title": item.metadata.title,
            "description": item.metadata.description,
            "tags": list(item.metadata.tags),
            "categoryId": category_id,
            "defaultLanguage": "pl",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": made_for_kids,
            "embeddable": True,
            "license": "youtube",
            "publicStatsViewable": True,
        },
    }
    if schedule_publication:
        body["status"]["publishAt"] = (
            item.publish_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        )
    media = MediaFileUpload(str(item.video), chunksize=16 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
        notifySubscribers=notify_subscribers,
    )
    response = None
    retries = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress(f"{item.video.name}: {int(status.progress() * 100)}%")
        except HttpError as error:
            if error.resp.status not in RETRIABLE_CODES or retries >= 8:
                raise
            retries += 1
            delay = random.random() * (2**retries)
            progress(f"Błąd chwilowy {error.resp.status}; ponawiam za {delay:.1f} s.")
            time.sleep(delay)
    video_id = response["id"]
    return video_id


def set_thumbnail(youtube, video_id: str, thumbnail: Path) -> None:
    mimetype = "image/png" if thumbnail.suffix.casefold() == ".png" else "image/jpeg"
    _execute_with_retry(
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail), mimetype=mimetype),
        )
    )


def _normalise_playlist_title(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def ensure_playlist(youtube, title: str) -> str:
    target = _normalise_playlist_title(title)
    token = None
    while True:
        response = _execute_with_retry(
            youtube.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50,
                pageToken=token,
            )
        )
        for playlist in response.get("items", []):
            if _normalise_playlist_title(playlist["snippet"]["title"]) == target:
                return playlist["id"]
        token = response.get("nextPageToken")
        if not token:
            break
    created = _execute_with_retry(
        youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": f"Wszystkie odcinki z serii {title} na kanale Divithyツ.",
                    "defaultLanguage": "pl",
                },
                "status": {"privacyStatus": "public"},
            },
        )
    )
    return created["id"]


def add_to_playlist(youtube, playlist_id: str, video_id: str) -> None:
    existing = _execute_with_retry(
        youtube.playlistItems().list(
            part="id",
            playlistId=playlist_id,
            videoId=video_id,
            maxResults=1,
        )
    )
    if existing.get("items"):
        return
    _execute_with_retry(
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        )
    )


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"uploads": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
