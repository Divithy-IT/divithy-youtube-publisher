from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from planner import QueueItem, build_queue, discover_packages, queue_as_json


APP_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = Path.home() / "Documents" / "Filmy YouTube"
CONFIG_FILE = APP_DIR / "publisher_config.json"
TOKEN_FILE = APP_DIR / "token.json"
STATE_FILE = APP_DIR / "upload_state.json"
QUEUE_FILE = APP_DIR / "ostatni_plan_publikacji.json"


class PublisherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Divithy Publisher")
        self.geometry("1120x720")
        self.minsize(900, 620)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.items: list[QueueItem] = []
        self.youtube = None
        self.config_data = self.load_config()
        self.build_ui()
        self.after(150, self.poll_events)

    def load_config(self) -> dict:
        defaults = {
            "content_root": str(DEFAULT_ROOT),
            "start_date": date.today().isoformat(),
            "timezone": "Europe/Warsaw",
            "game_order": "L4D2,PUBG",
            "type_order": "kompilacja,pelna_rozgrywka",
            "playlist_names": "L4D2=Left 4 Dead 2;PUBG=PUBG;CS2=Counter-Strike 2",
            "category_id": "20",
            "notify_main": True,
            "notify_shorts": False,
            "made_for_kids": False,
            "api_audited": False,
            "client_secret": "",
        }
        if CONFIG_FILE.exists():
            defaults.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        return defaults

    def save_config(self) -> None:
        data = {
            "content_root": self.root_var.get().strip(),
            "start_date": self.start_var.get().strip(),
            "timezone": self.timezone_var.get().strip(),
            "game_order": self.games_var.get().strip(),
            "type_order": self.types_var.get().strip(),
            "playlist_names": self.playlists_var.get().strip(),
            "category_id": self.category_var.get().strip(),
            "notify_main": self.notify_main_var.get(),
            "notify_shorts": self.notify_shorts_var.get(),
            "made_for_kids": self.kids_var.get(),
            "api_audited": self.audited_var.get(),
            "client_secret": self.secret_var.get().strip(),
        }
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def build_ui(self) -> None:
        panel = ttk.Frame(self, padding=16)
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(1, weight=1)
        panel.rowconfigure(10, weight=1)

        self.root_var = tk.StringVar(value=self.config_data["content_root"])
        self.start_var = tk.StringVar(value=self.config_data["start_date"])
        self.timezone_var = tk.StringVar(value=self.config_data["timezone"])
        self.games_var = tk.StringVar(value=self.config_data["game_order"])
        self.types_var = tk.StringVar(value=self.config_data["type_order"])
        self.playlists_var = tk.StringVar(value=self.config_data["playlist_names"])
        self.category_var = tk.StringVar(value=self.config_data["category_id"])
        self.secret_var = tk.StringVar(value=self.config_data["client_secret"])
        self.notify_main_var = tk.BooleanVar(value=self.config_data["notify_main"])
        self.notify_shorts_var = tk.BooleanVar(value=self.config_data["notify_shorts"])
        self.kids_var = tk.BooleanVar(value=self.config_data["made_for_kids"])
        self.audited_var = tk.BooleanVar(value=self.config_data["api_audited"])
        self.real_upload_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Tryb bezpieczny: nic nie zostanie wysłane.")

        self.row(panel, 0, "Folder z filmami", self.root_var, self.choose_root)
        self.row(panel, 1, "Plik OAuth JSON", self.secret_var, self.choose_secret)
        self.row(panel, 2, "Pierwszy dzień", self.start_var)
        self.row(panel, 3, "Strefa czasowa", self.timezone_var)
        self.row(panel, 4, "Kolejność gier", self.games_var)
        self.row(panel, 5, "Kolejność typów", self.types_var)
        self.row(panel, 6, "Nazwy playlist", self.playlists_var)
        self.row(panel, 7, "Kategoria YouTube", self.category_var)

        options = ttk.Frame(panel)
        options.grid(row=8, column=0, columnspan=3, sticky="w", pady=(8, 10))
        ttk.Checkbutton(options, text="Powiadamiaj przy filmach", variable=self.notify_main_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(options, text="Powiadamiaj przy shortsach", variable=self.notify_shorts_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(options, text="Treści dla dzieci", variable=self.kids_var).pack(side="left")
        ttk.Checkbutton(
            options,
            text="Projekt API przeszedł audyt (włącz harmonogram publiczny)",
            variable=self.audited_var,
        ).pack(side="left", padx=(16, 0))

        actions = ttk.Frame(panel)
        actions.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        ttk.Button(actions, text="1. Przygotuj podgląd", command=self.preview).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="2. Połącz z YouTube", command=self.authorize).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(actions, text="Zezwalam na prawdziwe wysyłanie", variable=self.real_upload_var).pack(side="left", padx=12)
        ttk.Button(actions, text="3. Wyślij i zaplanuj", command=self.start_upload).pack(side="right")

        columns = ("date", "game", "package", "kind", "title", "status")
        self.tree = ttk.Treeview(panel, columns=columns, show="headings")
        headings = {
            "date": "Publikacja", "game": "Gra", "package": "Paczka",
            "kind": "Typ", "title": "Tytuł", "status": "Stan",
        }
        widths = {"date": 145, "game": 70, "package": 80, "kind": 65, "title": 520, "status": 110}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")
        self.tree.grid(row=10, column=0, columnspan=3, sticky="nsew")
        scroll = ttk.Scrollbar(panel, orient="vertical", command=self.tree.yview)
        scroll.grid(row=10, column=3, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        ttk.Label(panel, textvariable=self.status_var).grid(row=11, column=0, columnspan=3, sticky="w", pady=(10, 0))

    def row(self, parent, row: int, label: str, variable: tk.StringVar, action=None) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=4)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)
        if action:
            ttk.Button(parent, text="Wybierz…", command=action).grid(row=row, column=2, padx=(8, 0), pady=4)

    def choose_root(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.root_var.get() or str(DEFAULT_ROOT))
        if chosen:
            self.root_var.set(chosen)

    def choose_secret(self) -> None:
        chosen = filedialog.askopenfilename(filetypes=[("Google OAuth JSON", "*.json")])
        if chosen:
            self.secret_var.set(chosen)

    def preview(self) -> None:
        try:
            self.save_config()
            packages = discover_packages(Path(self.root_var.get()))
            preferred = [game.strip() for game in self.games_var.get().split(",") if game.strip()]
            preferred_types = [kind.strip() for kind in self.types_var.get().split(",") if kind.strip()]
            self.items = build_queue(
                packages,
                date.fromisoformat(self.start_var.get()),
                self.timezone_var.get(),
                preferred,
                preferred_types,
            )
            QUEUE_FILE.write_text(queue_as_json(self.items), encoding="utf-8")
            self.refresh_tree()
            self.status_var.set(f"Gotowy podgląd: {len(packages)} paczki, {len(self.items)} publikacji. Nic nie wysłano.")
        except Exception as error:
            messagebox.showerror("Nie udało się przygotować planu", str(error))

    def refresh_tree(self, state: dict | None = None) -> None:
        state = state or {"uploads": {}}
        self.tree.delete(*self.tree.get_children())
        for item in self.items:
            uploaded = state.get("uploads", {}).get(item.key)
            status = f"YouTube: {uploaded['video_id']}" if uploaded else "oczekuje"
            self.tree.insert(
                "", "end", iid=item.key,
                values=(
                    item.publish_at.strftime("%Y-%m-%d %H:%M"),
                    item.package.game,
                    item.package.folder.name,
                    "SHORT" if item.kind == "short" else item.package.content_type.upper(),
                    item.metadata.title,
                    status,
                ),
            )

    def authorize(self) -> None:
        secret = Path(self.secret_var.get())
        if not secret.is_file():
            messagebox.showerror("Brak pliku OAuth", "Wskaż pobrany z Google plik JSON klienta OAuth.")
            return
        self.save_config()
        self.status_var.set("Otwieram bezpieczne logowanie Google w przeglądarce…")

        def worker():
            try:
                from youtube_api import authenticate
                service = authenticate(secret, TOKEN_FILE)
                self.events.put(("authorized", service))
            except Exception as error:
                self.events.put(("error", error))

        threading.Thread(target=worker, daemon=True).start()

    def start_upload(self) -> None:
        if not self.items:
            self.preview()
            if not self.items:
                return
        if not self.real_upload_var.get():
            messagebox.showinfo("Tryb bezpieczny", "Zaznacz pole zezwalające na prawdziwe wysyłanie.")
            return
        if self.youtube is None:
            messagebox.showerror("Brak połączenia", "Najpierw kliknij „Połącz z YouTube”.")
            return
        if not self.audited_var.get():
            messagebox.showwarning(
                "Najpierw audyt projektu API",
                "Dla bezpieczeństwa publikator nie wyśle gotowych materiałów przez "
                "nieaudytowany projekt. YouTube może zablokować takie pliki jako "
                "prywatne i wymagać ponownego przesłania. Wykonaj audyt projektu, "
                "a potem zaznacz odpowiednie pole.",
            )
            return
        if not messagebox.askyesno(
            "Potwierdź wysyłanie",
            f"Program wyśle i zaplanuje {len(self.items)} pozycji. Kontynuować?",
        ):
            return
        options = {
            "notify_main": self.notify_main_var.get(),
            "notify_shorts": self.notify_shorts_var.get(),
            "category_id": self.category_var.get(),
            "made_for_kids": self.kids_var.get(),
            "api_audited": self.audited_var.get(),
            "playlist_names": self.playlists_var.get(),
        }
        self.status_var.set("Rozpoczynam wysyłanie…")
        threading.Thread(target=self.upload_worker, args=(options,), daemon=True).start()

    def upload_worker(self, options: dict) -> None:
        from youtube_api import (
            add_to_playlist,
            ensure_playlist,
            load_state,
            save_state,
            set_thumbnail,
            upload_video,
        )
        state = load_state(STATE_FILE)
        playlist_names = {}
        for entry in options["playlist_names"].split(";"):
            game, separator, title = entry.partition("=")
            if separator and game.strip() and title.strip():
                playlist_names[game.strip()] = title.strip()
        playlist_cache: dict[str, str] = {}
        try:
            for position, item in enumerate(self.items, start=1):
                existing = state["uploads"].get(item.key)
                if existing:
                    if item.thumbnail and not existing.get("thumbnail_set", False):
                        self.events.put(("log", f"Uzupełniam miniaturę: {item.video.name}"))
                        set_thumbnail(self.youtube, existing["video_id"], item.thumbnail)
                        existing["thumbnail_set"] = True
                        save_state(STATE_FILE, state)
                        self.events.put(("uploaded", (item.key, existing["video_id"])))
                        continue
                    if item.kind == "film" and not existing.get("playlist_added", False):
                        playlist_title = playlist_names.get(item.package.game, item.package.game)
                        playlist_id = playlist_cache.get(playlist_title)
                        if not playlist_id:
                            playlist_id = ensure_playlist(self.youtube, playlist_title)
                            playlist_cache[playlist_title] = playlist_id
                        add_to_playlist(self.youtube, playlist_id, existing["video_id"])
                        existing["playlist_added"] = True
                        existing["playlist_id"] = playlist_id
                        save_state(STATE_FILE, state)
                        self.events.put(("uploaded", (item.key, existing["video_id"])))
                        continue
                    self.events.put(("log", f"Pomijam już wysłany plik: {item.video.name}"))
                    continue
                self.events.put(("log", f"[{position}/{len(self.items)}] {item.video.name}"))
                video_id = upload_video(
                    self.youtube,
                    item,
                    options["notify_main"] if item.kind == "film" else options["notify_shorts"],
                    options["category_id"],
                    options["made_for_kids"],
                    options["api_audited"],
                    lambda text: self.events.put(("log", text)),
                )
                state["uploads"][item.key] = {
                    "video_id": video_id,
                    "video": str(item.video),
                    "publish_at": item.publish_at.isoformat(),
                    "scheduled": options["api_audited"],
                    "thumbnail_set": item.thumbnail is None,
                    "playlist_added": item.kind != "film",
                }
                save_state(STATE_FILE, state)
                if item.thumbnail:
                    set_thumbnail(self.youtube, video_id, item.thumbnail)
                    state["uploads"][item.key]["thumbnail_set"] = True
                    save_state(STATE_FILE, state)
                if item.kind == "film":
                    playlist_title = playlist_names.get(item.package.game, item.package.game)
                    playlist_id = playlist_cache.get(playlist_title)
                    if not playlist_id:
                        playlist_id = ensure_playlist(self.youtube, playlist_title)
                        playlist_cache[playlist_title] = playlist_id
                    add_to_playlist(self.youtube, playlist_id, video_id)
                    state["uploads"][item.key]["playlist_added"] = True
                    state["uploads"][item.key]["playlist_id"] = playlist_id
                    save_state(STATE_FILE, state)
                self.events.put(("uploaded", (item.key, video_id)))
            self.events.put(("done", None))
        except Exception as error:
            self.events.put(("error", error))

    def poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "authorized":
                    self.youtube = payload
                    self.status_var.set("Połączono z YouTube. Nadal nic nie wysłano.")
                elif kind == "log":
                    self.status_var.set(str(payload))
                elif kind == "uploaded":
                    key, video_id = payload
                    if self.tree.exists(key):
                        values = list(self.tree.item(key, "values"))
                        values[-1] = f"YouTube: {video_id}"
                        self.tree.item(key, values=values)
                elif kind == "done":
                    self.real_upload_var.set(False)
                    self.status_var.set("Wysyłanie zakończone. Sprawdź kolejkę w YouTube Studio.")
                    messagebox.showinfo("Gotowe", "Wszystkie niewysłane pozycje zostały obsłużone.")
                elif kind == "error":
                    self.real_upload_var.set(False)
                    self.status_var.set("Wystąpił błąd — szczegóły w komunikacie.")
                    messagebox.showerror("Błąd", str(payload))
        except queue.Empty:
            pass
        self.after(150, self.poll_events)


if __name__ == "__main__":
    PublisherApp().mainloop()
