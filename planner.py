from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Metadata:
    title: str
    description: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Package:
    folder: Path
    number: int
    game: str
    content_type: str
    main_video: Path
    thumbnail: Path | None
    main_metadata: Metadata
    shorts: tuple[tuple[Path, Metadata], ...]


@dataclass(frozen=True)
class QueueItem:
    package: Package
    kind: str
    index: int
    video: Path
    thumbnail: Path | None
    metadata: Metadata
    publish_at: datetime

    @property
    def key(self) -> str:
        stat = self.video.stat()
        raw = f"{self.video.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _metadata_from_block(lines: list[str]) -> Metadata:
    title = ""
    description_lines: list[str] = []
    tags: tuple[str, ...] = ()
    in_description = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("Tytuł:"):
            title = line.partition(":")[2].strip()
            in_description = False
        elif line == "Opis:":
            in_description = True
        elif line.startswith("Tagi:"):
            tags = tuple(tag.strip() for tag in line.partition(":")[2].split(",") if tag.strip())
            in_description = False
        elif in_description:
            description_lines.append(raw.rstrip())
    description = "\n".join(description_lines).strip()
    if not title:
        raise ValueError("Brakuje pola „Tytuł:” w pliku metadanych.")
    if len(title) > 100:
        raise ValueError(f"Tytuł przekracza limit 100 znaków: {title}")
    if len(description) > 5000:
        raise ValueError(f"Opis przekracza limit 5000 znaków: {title}")
    if len(",".join(tags)) > 500:
        raise ValueError(f"Tagi przekraczają limit 500 znaków: {title}")
    return Metadata(title=title, description=description, tags=tags)


def read_metadata(path: Path) -> dict[str, Metadata]:
    text = path.read_text(encoding="utf-8-sig")
    headers = re.compile(r"^(FILM GŁÓWNY|SHORT\s+\d+)\s*$", re.MULTILINE)
    matches = list(headers.finditer(text))
    result: dict[str, Metadata] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end].strip().splitlines()
        result[match.group(1)] = _metadata_from_block(block)
    return result


def infer_game(title: str, folder: Path) -> str:
    override = folder / "gra.txt"
    if override.exists():
        value = override.read_text(encoding="utf-8-sig").strip()
        if value:
            return value
    value = title.casefold()
    if "left 4 dead" in value or "l4d" in value:
        return "L4D2"
    if "pubg" in value or "battlegrounds" in value:
        return "PUBG"
    if "counter-strike" in value or "counter strike" in value or "cs2" in value:
        return "CS2"
    return "INNE"


def infer_content_type(folder: Path, short_count: int) -> str:
    override = folder / "typ.txt"
    if override.exists():
        value = override.read_text(encoding="utf-8-sig").strip()
        if value:
            return value
    return "kompilacja" if short_count else "pelna_rozgrywka"


def discover_packages(root: Path) -> list[Package]:
    packages: list[Package] = []
    for folder in sorted((path for path in root.iterdir() if path.is_dir()), key=lambda p: p.name):
        number_match = re.search(r"(\d+)", folder.name)
        if not number_match:
            continue
        metadata_files = list(folder.glob("YouTube*.txt"))
        if not metadata_files:
            continue
        parsed = read_metadata(metadata_files[0])
        main_candidates = [
            path for path in folder.glob("*.mp4")
            if "zapowiedz" not in path.name.casefold() and "short" not in path.name.casefold()
        ]
        short_candidates = sorted(
            path for path in folder.glob("*.mp4")
            if "zapowiedz" in path.name.casefold() or "short" in path.name.casefold()
        )
        if len(main_candidates) != 1:
            raise ValueError(f"{folder.name}: oczekiwano jednego filmu głównego, znaleziono {len(main_candidates)}.")
        if len(short_candidates) not in (0, 3):
            raise ValueError(
                f"{folder.name}: paczka może mieć zero albo trzy shortsy, znaleziono {len(short_candidates)}."
            )
        if "FILM GŁÓWNY" not in parsed:
            raise ValueError(f"{folder.name}: brakuje sekcji FILM GŁÓWNY.")
        short_items: list[tuple[Path, Metadata]] = []
        for index, video in enumerate(short_candidates, start=1):
            key = f"SHORT {index}"
            if key not in parsed:
                raise ValueError(f"{folder.name}: brakuje sekcji {key}.")
            short_items.append((video, parsed[key]))
        thumbnails = sorted(folder.glob("Miniatura*.jpg")) + sorted(folder.glob("Miniatura*.png"))
        main_metadata = parsed["FILM GŁÓWNY"]
        packages.append(
            Package(
                folder=folder,
                number=int(number_match.group(1)),
                game=infer_game(main_metadata.title, folder),
                content_type=infer_content_type(folder, len(short_candidates)),
                main_video=main_candidates[0],
                thumbnail=thumbnails[0] if thumbnails else None,
                main_metadata=main_metadata,
                shorts=tuple(short_items),
            )
        )
    return packages


def _alternate_types(packages: list[Package], preferred_types: list[str]) -> list[Package]:
    grouped: dict[str, list[Package]] = {}
    for package in sorted(packages, key=lambda item: item.number):
        grouped.setdefault(package.content_type, []).append(package)
    order = [kind for kind in preferred_types if kind in grouped]
    order.extend(kind for kind in grouped if kind not in order)
    result: list[Package] = []
    while any(grouped.values()):
        for kind in order:
            if grouped.get(kind):
                result.append(grouped[kind].pop(0))
    return result


def round_robin(
    packages: Iterable[Package],
    preferred_games: list[str],
    preferred_types: list[str],
) -> list[Package]:
    grouped: dict[str, list[Package]] = {}
    for package in sorted(packages, key=lambda item: item.number):
        grouped.setdefault(package.game, []).append(package)
    grouped = {
        game: _alternate_types(game_packages, preferred_types)
        for game, game_packages in grouped.items()
    }
    order = [game for game in preferred_games if game in grouped]
    order.extend(game for game in grouped if game not in order)
    result: list[Package] = []
    while any(grouped.values()):
        for game in order:
            if grouped.get(game):
                result.append(grouped[game].pop(0))
    return result


def build_queue(
    packages: Iterable[Package],
    start_date: date,
    timezone: str = "Europe/Warsaw",
    preferred_games: list[str] | None = None,
    preferred_types: list[str] | None = None,
) -> list[QueueItem]:
    zone = ZoneInfo(timezone)
    result: list[QueueItem] = []
    ordered = round_robin(
        packages,
        preferred_games or ["L4D2", "PUBG"],
        preferred_types or ["kompilacja", "pelna_rozgrywka"],
    )
    cursor = start_date
    for package in ordered:
        for index, (video, metadata) in enumerate(package.shorts, start=1):
            result.append(
                QueueItem(
                    package=package,
                    kind="short",
                    index=index,
                    video=video,
                    thumbnail=None,
                    metadata=metadata,
                    publish_at=datetime.combine(cursor + timedelta(days=index - 1), time(15, 0), zone),
                )
            )
        result.append(
            QueueItem(
                package=package,
                kind="film",
                index=0,
                video=package.main_video,
                thumbnail=package.thumbnail,
                metadata=package.main_metadata,
                publish_at=datetime.combine(cursor + timedelta(days=2), time(18, 0), zone),
            )
        )
        cursor += timedelta(days=3)
    return sorted(result, key=lambda item: (item.publish_at, item.kind == "film"))


def queue_as_json(items: Iterable[QueueItem]) -> str:
    payload = [
        {
            "key": item.key,
            "game": item.package.game,
            "content_type": item.package.content_type,
            "package": item.package.folder.name,
            "kind": item.kind,
            "index": item.index,
            "video": str(item.video),
            "thumbnail": str(item.thumbnail) if item.thumbnail else None,
            "title": item.metadata.title,
            "description": item.metadata.description,
            "tags": list(item.metadata.tags),
            "publish_at_local": item.publish_at.isoformat(),
            "publish_at_utc": item.publish_at.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z"),
        }
        for item in items
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)
