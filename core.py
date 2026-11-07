"""Local process simulation. This module does not communicate with a Discord account."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import threading

from i18n import Message, MessageList, UserValueError, UserRuntimeError, tr

CATALOG_URL = "https://discord.com/api/v9/applications/detectable"
MAX_BYTES = 32 * 1024 * 1024
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


@dataclass(frozen=True)
class Game:
    id: str
    name: str
    executable: str


def safe_executable(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 180:
        return None
    value = value.replace("\\", "/")
    path = PureWindowsPath(value)
    if path.is_absolute() or path.drive or value.startswith("/"):
        return None
    parts = value.split("/")
    for part in parts:
        if (not part or part in {".", ".."} or part[-1:] in {" ", "."}
                or re.search(r'[<>:"|?*\x00-\x1f]', part)
                or part.split(".")[0].upper() in RESERVED):
            return None
    if not parts[-1].lower().endswith(".exe"):
        return None
    return "/".join(parts)


def executable_conflict_key(game: Game) -> str:
    """Use the same case-insensitive EXE basename for filtering and validation."""
    safe = safe_executable(game.executable)
    if safe is None:
        raise UserValueError("error.invalid_path", name=game.name)
    return PureWindowsPath(safe).name.casefold()


def filter_conflicting_games(games: list[Game]) -> tuple[list[Game], list[Game]]:
    """Keep the first game per EXE basename, preserving both output orders.

    Invalid paths raise before the caller changes its queue; they are never
    silently discarded as if they were executable-name conflicts.
    """
    kept, removed, seen = [], [], set()
    for game in games:
        key = executable_conflict_key(game)
        if key in seen:
            removed.append(game)
        else:
            kept.append(game)
            seen.add(key)
    return kept, removed


def parse_catalog(data: object) -> list[Game]:
    if not isinstance(data, list):
        raise UserValueError("error.catalog_schema")
    games = []
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        app_id, name = item.get("id"), item.get("name")
        if not isinstance(app_id, str) or not app_id.isdecimal() or not isinstance(name, str) or not name.strip():
            continue
        if app_id in seen:
            continue
        executables = item.get("executables", [])
        if not isinstance(executables, list):
            continue
        candidates = []
        for exe in executables:
            if not isinstance(exe, dict) or exe.get("os") != "win32" or exe.get("is_launcher"):
                continue
            safe = safe_executable(exe.get("name"))
            if safe:
                candidates.append(safe)
        if candidates:
            games.append(Game(app_id, name.strip()[:160], candidates[0]))
            seen.add(app_id)
    if not games:
        raise UserValueError("error.catalog_empty")
    return sorted(games, key=lambda g: (g.name.casefold(), g.id))


def read_catalog(path: Path) -> list[Game]:
    if path.stat().st_size > MAX_BYTES:
        raise UserValueError("error.catalog_large")
    return parse_catalog(json.loads(path.read_text(encoding="utf-8")))


def download_catalog(path: Path) -> list[Game]:
    request = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    start = time.monotonic()
    chunks, size = [], 0
    with urllib.request.urlopen(request, timeout=15) as response:
        while chunk := response.read(128 * 1024):
            size += len(chunk)
            if size > MAX_BYTES or time.monotonic() - start > 90:
                raise UserValueError("error.catalog_limit")
            chunks.append(chunk)
    raw = b"".join(chunks)
    games = parse_catalog(json.loads(raw))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)
    return games


HELPER_SOURCE = r'''
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text;
using System.Windows.Forms;
class IdleProcess {
    [STAThread]
    static int Main(string[] args) {
        try {
            if (args.Length != 3) return 2;
            using (Process parent = Process.GetProcessById(int.Parse(args[0]))) {
                // Acquire a handle now so PID reuse cannot attach us to a later process.
                IntPtr parentHandle = parent.Handle;
                Application.EnableVisualStyles();
                using (Form window = new Form())
                using (Timer watcher = new Timer()) {
                    window.BackColor = Color.FromArgb(16, 23, 34);
                    window.ForeColor = Color.FromArgb(230, 237, 245);
                    window.ClientSize = new Size(460, 140);
                    window.StartPosition = FormStartPosition.CenterScreen;
                    window.FormBorderStyle = FormBorderStyle.FixedSingle;
                    window.MaximizeBox = false;
                    window.ShowInTaskbar = true;
                    Label label = new Label();
                    label.Dock = DockStyle.Fill;
                    label.Padding = new Padding(16);
                    label.Font = new Font("Segoe UI", 10);
                    label.BackColor = window.BackColor;
                    label.ForeColor = window.ForeColor;
                    window.Controls.Add(label);
                    string previousText = null;
                    Action translate = delegate {
                        try {
                            string text;
                            // Permit the controller's atomic translation replacement.
                            using (FileStream file = new FileStream(args[2], FileMode.Open, FileAccess.Read,
                                    FileShare.ReadWrite | FileShare.Delete))
                            using (StreamReader reader = new StreamReader(file, Encoding.UTF8)) {
                                text = reader.ReadToEnd();
                            }
                            if (text == previousText) return;
                            string[] parts = text.Split(new char[] {'\n'}, 3);
                            if (parts.Length != 3) return;
                            bool light = parts[0].TrimEnd('\r') == "light";
                            window.BackColor = light ? Color.FromArgb(246, 248, 251) : Color.FromArgb(16, 23, 34);
                            window.ForeColor = light ? Color.FromArgb(31, 41, 55) : Color.FromArgb(230, 237, 245);
                            label.BackColor = window.BackColor;
                            label.ForeColor = window.ForeColor;
                            window.Text = args[1] + " — " + parts[1].TrimEnd('\r');
                            label.Text = parts[2];
                            previousText = text;
                        } catch (IOException) { }
                        catch (UnauthorizedAccessException) { }
                    };
                    translate();
                    watcher.Interval = 500;
                    watcher.Tick += delegate {
                        try { if (parent.HasExited) window.Close(); else translate(); }
                        catch { window.Close(); }
                    };
                    watcher.Start();
                    Application.Run(window);
                }
            }
            return 0;
        } catch { return 1; }
    }
}
'''

# Version all running files: a new app can coexist with an older helper without
# overwriting its locked executable or requiring termination of other processes.
HELPER_VERSION = hashlib.sha256(HELPER_SOURCE.encode("utf-8")).hexdigest()[:16]


class ProcessBackend:
    def __init__(self, cache: Path):
        # Packaged Windows apps may redirect LOCALAPPDATA only after a directory
        # exists. Resolve after creating this trusted base, otherwise later child
        # paths canonicalize into LocalCache while this base retains its alias.
        cache.mkdir(parents=True, exist_ok=True)
        self.cache = cache.resolve(strict=True)
        self.theme = "dark"
        self._appearance_lock = threading.RLock()

    @property
    def helper_language_path(self):
        return self.cache / ("helper-language-" + HELPER_VERSION + ".txt")

    def update_language(self):
        # Both language and theme share one atomically replaced watched file.
        with self._appearance_lock:
            path = self.helper_language_path
            text = self.theme + "\n" + tr("helper.suffix") + "\n" + tr("helper.body")
            if path.exists() and path.read_text(encoding="utf-8") == text:
                return
            temporary = path.with_suffix(".tmp")
            temporary.write_text(text, encoding="utf-8")
            temporary.replace(path)

    def set_theme(self, theme):
        if theme not in {"light", "dark"}:
            raise ValueError("Unsupported theme")
        with self._appearance_lock:
            self.theme = theme
            self.update_language()

    def compile_helper(self) -> Path:
        helper = self.cache / ("helper-" + HELPER_VERSION + ".exe")
        source = self.cache / ("helper-" + HELPER_VERSION + ".cs")
        self.cache.mkdir(parents=True, exist_ok=True)
        if helper.exists() and source.exists() and source.read_text(encoding="utf-8") == HELPER_SOURCE:
            return helper
        source.write_text(HELPER_SOURCE, encoding="utf-8")
        windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
        compilers = [windows / "Microsoft.NET" / directory / "v4.0.30319" / "csc.exe" for directory in ("Framework64", "Framework")]
        compiler = next((p for p in compilers if p.is_file()), None)
        if compiler is None:
            raise UserRuntimeError("error.compiler_missing")
        result = subprocess.run([str(compiler), "/nologo", "/target:winexe", "/optimize+", "/codepage:65001",
                                 "/reference:System.Windows.Forms.dll", "/reference:System.Drawing.dll", f"/out:{helper}", str(source)],
                                capture_output=True, timeout=40, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise UserRuntimeError("error.compile", details=result.stdout.decode(errors="replace")[:500])
        return helper

    def start(self, game: Game):
        safe = safe_executable(game.executable)
        if safe is None:
            raise UserValueError("error.unsafe_path")
        helper = self.compile_helper()
        self.update_language()
        key = hashlib.sha256(game.id.encode()).hexdigest()[:16]
        root = (self.cache / "processes" / HELPER_VERSION / key).resolve()
        if not root.is_relative_to(self.cache):
            raise UserValueError("error.path_escape")
        target = (root / safe).resolve()
        if not target.is_relative_to(self.cache) or not target.is_relative_to(root):
            raise UserValueError("error.path_escape")
        # All files here are our helper copies, never files in a real game installation.
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(helper, target)
        return subprocess.Popen([str(target), str(os.getpid()), game.name, str(self.helper_language_path)], cwd=target.parent,
                                creationflags=subprocess.CREATE_NO_WINDOW)

    def stop(self, process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


class Rotation:
    def __init__(self, backend, clock=time.monotonic, cancel_event=None):
        self.backend, self.clock = backend, clock
        self.cancel_event = cancel_event
        self.experimental_concurrency = False
        self.experimental_timing = False
        self.processes = []  # (Game, owned process); failed stops remain tracked.
        self.running = False
        self.games = []
        self.index = 0
        self.concurrency = 1
        self.started = self.changed = 0.0
        self.elapsed = 0.0
        self.interval = 0.0

    @property
    def active(self):
        return bool(self.processes)

    @property
    def process(self):
        return self.processes[0][1] if self.processes else None

    @property
    def current_games(self):
        return [game for game, process in self.processes]

    @property
    def current(self):
        return self.current_games[0] if self.active else None

    def start(self, games: list[Game], minutes: float, concurrency: int = 1, *,
              experimental_concurrency=False, experimental_timing=False, seconds=10):
        if self.active:
            raise UserValueError("error.active")
        if not isinstance(experimental_concurrency, bool) or not isinstance(experimental_timing, bool):
            raise UserValueError("error.mode")
        limit = 100 if experimental_concurrency else 10
        if isinstance(concurrency, bool) or not isinstance(concurrency, int) or not 1 <= concurrency <= limit:
            raise UserValueError("error.concurrent_limit", limit=limit)
        interval_value = seconds if experimental_timing else minutes
        minimum, maximum = (10, 86400) if experimental_timing else (1, 1440)
        if (not games or isinstance(interval_value, bool) or not isinstance(interval_value, (int, float))
                or not math.isfinite(interval_value) or not minimum <= interval_value <= maximum):
            raise UserValueError("error.seconds_interval" if experimental_timing else "error.interval")
        unique = {}
        for game in games:
            unique.setdefault(game.id, game)
        selected = list(unique.values())
        if concurrency > 1:
            basenames = {}
            for game in selected:
                basename = executable_conflict_key(game)
                if basename in basenames:
                    raise UserValueError("error.collision", exe=basename, first=basenames[basename], second=game.name)
                basenames[basename] = game.name
        self.games = selected
        self.index = 0
        self.concurrency = concurrency
        self.experimental_concurrency = experimental_concurrency
        self.experimental_timing = experimental_timing
        self.interval = seconds if experimental_timing else minutes * 60
        self.started = self.changed = self.clock()
        self.elapsed = 0.0
        self.running = True
        self._launch_cohort()

    def _launch_cohort(self):
        try:
            for game in self.games[self.index:self.index + self.concurrency]:
                self._check_cancelled()
                self.processes.append((game, self.backend.start(game)))
                self._check_cancelled()
            # Give even a slowly launched cohort its full dwell time.
            self.changed = self.clock()
        except Exception as launch_error:
            self.running = False
            try:
                self.stop_process()
            except Exception as stop_error:
                raise UserRuntimeError("error.group_launch", launch=launch_error, stop=stop_error) from launch_error
            raise

    def _check_cancelled(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise UserRuntimeError("error.cancelled")

    def tick(self):
        if not self.running:
            return
        now = self.clock()
        self.elapsed = now - self.started
        try:
            exited = [game.name for game, process in self.processes if process.poll() is not None]
        except Exception as poll_error:
            self.running = False
            try:
                self.stop_process()
            except Exception as stop_error:
                raise UserRuntimeError("error.poll_cleanup", error=poll_error, stop=stop_error) from poll_error
            raise UserRuntimeError("error.poll_stopped", error=poll_error) from poll_error
        if exited:
            self.running = False
            try:
                self.stop_process()
            except Exception as stop_error:
                raise UserRuntimeError("error.exited_cleanup", names=", ".join(exited), stop=stop_error) from stop_error
            raise UserRuntimeError("error.exited_stopped", names=", ".join(exited))
        if now - self.changed >= self.interval and len(self.games) > self.concurrency:
            # Stop the full old cohort before launching any new member.
            try:
                self.stop_process()
            except Exception:
                self.running = False
                raise
            following = self.index + self.concurrency
            self.index = following if following < len(self.games) else 0
            self._launch_cohort()
            self.changed = self.clock()

    def stop_process(self):
        remaining, errors = [], []
        for game, process in self.processes:
            try:
                self.backend.stop(process)
                if process.poll() is None:
                    raise UserRuntimeError("error.still_running")
            except Exception as error:
                # Retain ownership even if we cannot establish whether it exited.
                remaining.append((game, process))
                errors.append(Message("error.process", name=game.name, error=error))
        self.processes = remaining
        if errors:
            raise UserRuntimeError("error.stop", errors=MessageList(errors))

    def stop(self):
        if self.running:
            self.elapsed = self.clock() - self.started
        self.running = False
        self.stop_process()
