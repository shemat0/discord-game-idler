"""Bilingual desktop front end for experimental Discord game detection."""
import os
from pathlib import Path
import queue
import threading
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

from core import ProcessBackend, Rotation, download_catalog, read_catalog, filter_conflicting_games
from i18n import Message, UserValueError, tr, set_language, current_language, load_language, save_language
from version import __version__


def cache_directory():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "DiscordGameIdler"


class App:
    def __init__(self, root):
        self.root = root
        root.geometry("980x840")
        root.minsize(800, 760)
        self.cache = cache_directory()
        self.preferences_path = self.cache / "settings.json"
        set_language(load_language(self.preferences_path))
        self.catalog_path = self.cache / "catalog.json"
        self._cancel_event = threading.Event()
        self.rotation = Rotation(ProcessBackend(self.cache), cancel_event=self._cancel_event)
        self._operation_busy = False
        self._stop_requested = False
        self._closing = False
        self._next_tick = 0.0
        self.games, self.visible, self.selected = [], {}, {}
        self.messages = queue.Queue()
        self.loading = False
        self._text_widgets = []
        self._message_specs = {}
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self.filter())
        self.minutes = tk.StringVar(value="15")
        self.concurrency = tk.StringVar(value="10")
        self.experimental = tk.BooleanVar(value=False)
        self.status = tk.StringVar()
        self.session = tk.StringVar()
        self.catalog_status = tk.StringVar()
        self.set_message(self.status, "status.initial")
        self.set_message(self.catalog_status, "catalog.initial")
        self.set_message(self.session, "session.stopped")
        outer = ttk.Frame(root, padding=20)
        outer.pack(fill="both", expand=True)
        top = ttk.Frame(outer)
        top.pack(fill="x")
        self.label(top, "app.heading", font=("Segoe UI", 22, "bold")).pack(side="left")
        self.language = tk.StringVar(value="Русский" if current_language() == "ru" else "English")
        self.language_input = ttk.Combobox(top, values=("Русский", "English"), textvariable=self.language,
                                           state="readonly", width=10)
        self.language_input.pack(side="right")
        self.language_input.bind("<<ComboboxSelected>>", self.change_language)
        ttk.Label(top, text="Язык / Language").pack(side="right", padx=8)
        self.label(outer, "app.subtitle", font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 10))
        self.label(outer, "app.intro", wraplength=900).pack(anchor="w", pady=(0, 14))
        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x")
        ttk.Entry(toolbar, textvariable=self.search).pack(side="left", fill="x", expand=True)
        self.refresh = self.button(toolbar, "app.refresh", command=self.load_remote)
        self.refresh.pack(side="left", padx=(10, 0))
        ttk.Label(outer, textvariable=self.catalog_status).pack(anchor="w", pady=(5, 8))
        middle = ttk.Frame(outer)
        middle.pack(fill="both", expand=True)
        left = ttk.Frame(middle)
        left.pack(side="left", fill="both", expand=True)
        self.tree = ttk.Treeview(left, columns=("name", "exe"), show="headings", selectmode="extended", height=12)
        self.tree.column("name", width=250)
        self.tree.column("exe", width=200)
        scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _: self.add())
        right = ttk.Frame(middle, padding=(14, 0, 0, 0))
        right.pack(side="left", fill="both")
        self.label(right, "app.queue", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.chosen = tk.Listbox(right, width=28, selectmode="extended", exportselection=False)
        self.chosen.pack(fill="both", expand=True, pady=6)
        self.button(right, "app.add", command=self.add).pack(fill="x")
        self.button(right, "app.remove", command=self.remove).pack(fill="x", pady=(5, 0))
        self.filter_conflicts_button = self.button(right, "app.filter", command=self.filter_conflicts)
        self.filter_conflicts_button.pack(fill="x", pady=(5, 0))
        self.clear_queue_button = self.button(right, "app.clear_queue", command=self.clear_queue)
        self.clear_queue_button.pack(fill="x", pady=(5, 0))
        self.experimental_input = ttk.Checkbutton(outer, variable=self.experimental, command=self.change_mode)
        self._text_widgets.append((self.experimental_input, "app.experimental"))
        self.experimental_input.pack(anchor="w", pady=(10, 0))
        self.mode_note = tk.StringVar()
        ttk.Label(outer, textvariable=self.mode_note, wraplength=900).pack(anchor="w", pady=(3, 0))
        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(16, 8))
        self.label(controls, "app.concurrent").pack(side="left")
        self.concurrency_input = ttk.Spinbox(controls, from_=1, to=10, width=5, textvariable=self.concurrency)
        self.concurrency_input.pack(side="left", padx=6)
        self.max_note = tk.StringVar()
        ttk.Label(controls, textvariable=self.max_note).pack(side="left")
        self.start_button = self.button(controls, "app.start", command=self.start)
        self.start_button.pack(side="right")
        self.stop_button = self.button(controls, "app.stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="right", padx=8)
        interval = ttk.Frame(outer)
        interval.pack(fill="x", pady=(0, 5))
        self.label(interval, "app.interval").pack(side="left")
        self.minutes_input = ttk.Spinbox(interval, from_=1, to=1440, width=7, textvariable=self.minutes)
        self.minutes_input.pack(side="left", padx=6)
        self.label(interval, "app.minutes", wraplength=560).pack(side="left")
        self.interval_frame = interval
        self.experimental_interval = self.label(outer, "app.experimental_interval", wraplength=900)
        self.session_label = ttk.Label(outer, textvariable=self.session, font=("Segoe UI", 12, "bold"), wraplength=900)
        self.session_label.pack(anchor="w", pady=6)
        active_frame = ttk.Frame(outer)
        active_frame.pack(fill="x", pady=(0, 6))
        self.active_games = tk.Listbox(active_frame, height=3, exportselection=False)
        active_scroll = ttk.Scrollbar(active_frame, orient="vertical", command=self.active_games.yview)
        self.active_games.configure(yscrollcommand=active_scroll.set)
        active_scroll.pack(side="right", fill="y")
        self.active_games.pack(fill="x", expand=True)
        ttk.Label(outer, textvariable=self.status, wraplength=900).pack(anchor="w")
        self.label(outer, "app.timer_note", wraplength=900).pack(anchor="w", pady=(8, 0))
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.render_language()
        self.apply_mode()
        self.load_cache()
        root.after(250, self.update)

    def label(self, parent, key, **options):
        widget = ttk.Label(parent, text=tr(key), **options)
        self._text_widgets.append((widget, key))
        return widget

    def button(self, parent, key, **options):
        widget = ttk.Button(parent, text=tr(key), **options)
        self._text_widgets.append((widget, key))
        return widget

    def set_message(self, variable, key, **values):
        # Store semantic messages, so an already displayed error translates live.
        if not hasattr(self, "_message_specs"):
            self._message_specs = {}
        message = Message(key, **values)
        self._message_specs[id(variable)] = (variable, message)
        variable.set(str(message))

    def render_language(self):
        self.root.title(f"{tr('app.title')} • {__version__}")
        for widget, key in self._text_widgets:
            widget.configure(text=tr(key))
        self.tree.heading("name", text=tr("app.game"))
        self.tree.heading("exe", text=tr("app.process"))
        for variable, message in self._message_specs.values():
            variable.set(str(message))

    def change_language(self, _event=None):
        if getattr(self, "_operation_busy", False):
            self.language.set("Русский" if current_language() == "ru" else "English")
            return
        set_language("ru" if self.language.get() == "Русский" else "en")
        self.render_language()
        try:
            self.rotation.backend.update_language()
            save_language(self.preferences_path, current_language())
        except OSError as error:
            self.set_message(self.status, "status.language_error", error=error)

    def locked(self):
        return self.rotation.active or getattr(self, "_operation_busy", False)

    def change_mode(self):
        if self.locked():
            self.experimental.set(self.rotation.experimental)
            return
        if self.experimental.get():
            self.concurrency.set("100")
        else:
            self.concurrency.set("10")
            self.minutes.set("15")
        self.apply_mode()

    def apply_mode(self):
        experimental = self.experimental.get()
        self.concurrency_input.configure(to=100 if experimental else 10)
        self.set_message(self.max_note, "app.max_experimental" if experimental else "app.max")
        self.set_message(self.mode_note, "app.experimental_note" if experimental else "app.normal_note")
        # Both rows occupy the same position, so mode changes do not disturb the queue.
        if experimental:
            self.interval_frame.pack_forget()
            self.experimental_interval.pack(fill="x", before=self.session_label, pady=(0, 5))
        else:
            self.experimental_interval.pack_forget()
            self.interval_frame.pack(fill="x", before=self.session_label, pady=(0, 5))

    def load_cache(self):
        bundled = Path(__file__).resolve().with_name("catalog.json")
        for path in (self.catalog_path, bundled):
            if not path.exists():
                continue
            try:
                self.games = read_catalog(path)
                self.set_message(self.catalog_status, "catalog.cached" if path == self.catalog_path else "catalog.bundled", count=len(self.games))
                self.set_message(self.status, "status.choose")
                self.filter()
                return
            except Exception as error:
                self.set_message(self.status, "status.cache_error", error=error)

    def load_remote(self):
        if self.loading:
            return
        self.loading = True
        self.refresh.configure(state="disabled")
        self.set_message(self.catalog_status, "catalog.loading")
        def fetch():
            try:
                self.messages.put(("catalog", download_catalog(self.catalog_path)))
            except Exception as error:
                self.messages.put(("error", error))
        threading.Thread(target=fetch, daemon=True).start()

    def filter(self):
        query = self.search.get().strip().casefold()
        self.tree.delete(*self.tree.get_children())
        self.visible.clear()
        for game in self.games:
            if query in game.name.casefold() or query in game.executable.casefold():
                self.visible[game.id] = game
                self.tree.insert("", "end", iid=game.id, values=(game.name, game.executable))

    def redraw_queue(self):
        self.chosen.delete(0, "end")
        for game in self.selected.values():
            self.chosen.insert("end", game.name)

    def add(self):
        if self.locked():
            return
        for key in self.tree.selection():
            self.selected[key] = self.visible[key]
        self.redraw_queue()

    def remove(self):
        if self.locked():
            return
        keys = list(self.selected)
        for index in reversed(self.chosen.curselection()):
            del self.selected[keys[index]]
        self.redraw_queue()

    def filter_conflicts(self):
        if self.locked():
            return
        if not self.selected:
            self.set_message(self.status, "status.empty")
            return
        try:
            kept, removed = filter_conflicting_games(list(self.selected.values()))
        except ValueError as error:
            self.set_message(self.status, "status.unchanged", error=error)
            return
        if not removed:
            self.set_message(self.status, "status.no_conflicts", count=len(kept))
            return
        self.selected = {game.id: game for game in kept}
        self.redraw_queue()
        self.set_message(self.status, "status.filtered", removed=len(removed), kept=len(kept))
        details = "\n".join("• " + (game.name if len(game.name) <= 80 else game.name[:79] + "…") for game in removed[:10])
        if len(removed) > 10:
            details += "\n" + tr("dialog.more", count=len(removed) - 10)
        messagebox.showinfo(tr("dialog.filtered_title"), tr("dialog.filtered_body", count=len(removed), details=details), parent=self.root)

    def clear_queue(self):
        if self.locked():
            return
        self.selected.clear()
        self.redraw_queue()
        self.set_message(self.status, "status.queue_cleared")

    def start(self):
        if self.locked():
            return
        try:
            try:
                minutes = 15.0 if self.experimental.get() else float(self.minutes.get().replace(",", "."))
                count = int(self.concurrency.get())
            except ValueError as error:
                raise UserValueError("error.experimental_numbers" if self.experimental.get() else "error.numbers") from error
            games = list(self.selected.values())
            experimental = self.experimental.get()
            self._cancel_event.clear()
            self._stop_requested = False
            self.set_message(self.status, "status.starting")
            self.run_operation("start", lambda: self.rotation.start(games, minutes, count, experimental=experimental))
        except Exception as error:
            self.set_message(self.status, "status.start_error", error=error)
            messagebox.showerror(tr("dialog.start_error"), str(error), parent=self.root)
            self.set_running(self.rotation.active)

    def run_operation(self, kind, operation):
        if self._operation_busy:
            return
        self._operation_busy = True
        self.set_running(True)
        def execute():
            try:
                operation()
                error = None
            except Exception as caught:
                error = caught
            self.messages.put(("operation", (kind, error)))
        threading.Thread(target=execute, daemon=True).start()

    def operation_finished(self, kind, error):
        self._operation_busy = False
        if kind in {"tick", "start"}:
            self._next_tick = time.monotonic() + .5
        if error is not None:
            self.set_message(self.status, "error.raw", error=error)
        elif kind in {"start", "stop"}:
            self.set_message(self.status, "status.running" if kind == "start" else "status.stopped")
        if self._stop_requested:
            self._stop_requested = False
            if kind != "stop" and self.rotation.active:
                self.run_operation("stop", self.rotation.stop)
                return True
        self.set_running(self.rotation.active)
        if self._closing:
            if self.rotation.active:
                self._closing = False
                messagebox.showerror(tr("dialog.close_title"), tr("dialog.close_error"), parent=self.root)
            else:
                self.root.destroy()
                return False
        return True

    def maybe_tick(self):
        if (not self._operation_busy and self.rotation.running
                and time.monotonic() >= self._next_tick):
            self.run_operation("tick", self.rotation.tick)

    def set_running(self, active):
        self.start_button.configure(state="disabled" if active else "normal")
        self.stop_button.configure(state="normal" if active else "disabled")
        self.concurrency_input.configure(state="disabled" if active else "normal")
        self.minutes_input.configure(state="disabled" if active else "normal")
        self.filter_conflicts_button.configure(state="disabled" if active else "normal")
        if hasattr(self, "clear_queue_button"):
            self.clear_queue_button.configure(state="disabled" if active else "normal")
        if hasattr(self, "experimental_input"):
            self.experimental_input.configure(state="disabled" if active else "normal")
        if hasattr(self, "language_input"):
            self.language_input.configure(state="disabled" if getattr(self, "_operation_busy", False) else "readonly")

    def stop(self):
        self._cancel_event.set()
        self.set_message(self.status, "status.stopping")
        if self._operation_busy:
            self._stop_requested = True
        else:
            self.run_operation("stop", self.rotation.stop)

    def update(self):
        try:
            while True:
                kind, value = self.messages.get_nowait()
                if kind == "operation":
                    if self.operation_finished(*value) is False:
                        return
                    continue
                self.loading = False
                self.refresh.configure(state="normal")
                if kind == "catalog":
                    self.games = value
                    self.set_message(self.catalog_status, "catalog.updated", count=len(value))
                    self.set_message(self.status, "status.choose_one")
                    self.filter()
                else:
                    self.set_message(self.catalog_status, "catalog.failed", count=len(self.games))
                    self.set_message(self.status, "status.catalog_error", error=value)
        except queue.Empty:
            pass
        self.maybe_tick()
        seconds = int(self.rotation.elapsed)
        elapsed = f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}"
        games = self.rotation.current_games
        key = "session.running" if self.rotation.running else ("session.pending" if games else "session.stopped")
        state = Message(key, count=len(games))
        self.set_message(self.session, "session.timer", state=state, time=elapsed)
        names = tuple(game.name for game in games)
        if tuple(self.active_games.get(0, "end")) != names:
            self.active_games.delete(0, "end")
            for name in names:
                self.active_games.insert("end", name)
        self.root.after(50, self.update)

    def close(self):
        self._closing = True
        self.stop()


if __name__ == "__main__":
    import ctypes
    set_language(load_language(cache_directory() / "settings.json"))
    # Held for the app lifetime; protects shared helper files from other instances.
    ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\DiscordGameIdler-2026")
    already_open = ctypes.windll.kernel32.GetLastError() == 183
    window = tk.Tk()
    if already_open:
        window.withdraw()
        messagebox.showinfo(tr("app.title"), tr("dialog.already_open"))
        window.destroy()
        sys.exit(0)
    ttk.Style().theme_use("vista")
    App(window)
    window.mainloop()
