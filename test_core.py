import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
import shutil
import ctypes
from ctypes import wintypes
from unittest.mock import patch, Mock
from types import SimpleNamespace

from core import Game, ProcessBackend, Rotation, parse_catalog, read_catalog, safe_executable, filter_conflicting_games


class CatalogTests(unittest.TestCase):
    def test_realistic_catalog_and_duplicates(self):
        data = [{"id": "10", "name": "Game", "executables": [
            {"os": "darwin", "name": "game.app"},
            {"os": "win32", "name": "launcher.exe", "is_launcher": True},
            {"os": "win32", "name": "bin\\game.exe"}]},
            {"id": "10", "name": "Duplicate", "executables": [{"os": "win32", "name": "game.exe"}]},
            {"id": "11", "name": "Other game", "executables": [{"os": "win32", "name": "bin/game.exe"}]},
            {"id": "12", "name": "Unsafe", "executables": [{"os": "win32", "name": "../bad.exe"}]},
            {"id": "13", "name": "Broken", "executables": None}]
        games = parse_catalog(data)
        self.assertEqual(len(games), 2)
        self.assertEqual(games[0], Game("10", "Game", "bin/game.exe"))
        self.assertEqual(games[1].executable, games[0].executable)

    def test_unsafe_paths(self):
        for value in (None, "", "../evil.exe", "a/../evil.exe", "C:/evil.exe", "C:evil.exe", "/evil.exe",
                      "//host/share/a.exe", "a//b.exe", "a/./b.exe", "a:stream.exe", "*.exe", "a?.exe",
                      "CON.exe", "a/NUL/x.exe", "game.exe ", "a /b.exe", "a\x00.exe", "noextension"):
            with self.subTest(value=value):
                self.assertIsNone(safe_executable(value))
        self.assertEqual(safe_executable("bin/game-x64.exe"), "bin/game-x64.exe")

    def test_bad_schema(self):
        for data in ({}, [], [None], [{"id": "not-number", "name": "x"}]):
            with self.assertRaises(ValueError):
                parse_catalog(data)


class FakeProcess:
    dead = False
    def poll(self):
        return 1 if self.dead else None


class FakeBackend:
    def __init__(self):
        self.events = []
        self.fail = False
        self.fail_at = None
        self.stop_fail_ids = set()
        self.children = []
    def start(self, game):
        self.events.append(("start", game.id))
        if self.fail or len([event for event in self.events if event[0] == "start"]) == self.fail_at:
            raise OSError("failed")
        child = FakeProcess()
        child.game_id = game.id
        self.children.append(child)
        return child
    def stop(self, process):
        if process.game_id in self.stop_fail_ids:
            raise OSError("stop failed")
        process.dead = True
        self.events.append(("stop",))


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.backend = FakeBackend()
        self.rotation = Rotation(self.backend, clock=lambda: self.now)
        self.games = [Game("1", "A", "a.exe"), Game("2", "B", "b.exe")]

    def test_rotation_boundary_and_stop(self):
        self.rotation.start(self.games, 1)
        self.now += 59.9
        self.rotation.tick()
        self.assertEqual(self.rotation.current.id, "1")
        self.now += .1
        self.rotation.tick()
        self.assertEqual(self.rotation.current.id, "2")
        self.assertEqual(self.backend.events, [("start", "1"), ("stop",), ("start", "2")])
        self.now += 60
        self.rotation.tick()
        self.assertEqual(self.rotation.current.id, "1")
        self.rotation.stop()
        self.rotation.stop()
        self.assertFalse(self.rotation.active)
        self.assertEqual(self.rotation.elapsed, 120)

    def test_validation_and_double_start(self):
        for minutes in (0, -1, float("nan"), float("inf"), 1441):
            with self.assertRaises(ValueError):
                self.rotation.start(self.games, minutes)
        with self.assertRaises(ValueError):
            self.rotation.start([], 1)
        self.rotation.start(self.games, 1)
        with self.assertRaises(ValueError):
            self.rotation.start(self.games, 1)

    def test_single_game_stays_running(self):
        self.rotation.start(self.games[:1], 1)
        self.now += 600
        self.rotation.tick()
        self.assertEqual(len(self.backend.events), 1)

    def test_failed_rotation_does_not_remain_active(self):
        self.rotation.start(self.games, 1)
        old = self.rotation.process
        self.backend.fail = True
        self.now += 60
        with self.assertRaises(OSError):
            self.rotation.tick()
        self.assertTrue(old.dead)
        self.assertFalse(self.rotation.active)

    def test_unexpected_exit(self):
        self.rotation.start(self.games, 1)
        self.rotation.process.dead = True
        with self.assertRaises(RuntimeError):
            self.rotation.tick()
        self.assertFalse(self.rotation.active)

    def many_games(self, count):
        return [Game(str(i), f"Game {i}", f"game-{i}.exe") for i in range(count)]

    def test_ten_simultaneous_starts_and_full_stop(self):
        self.rotation.start(self.many_games(10), 1, 10)
        self.assertEqual(len(self.rotation.current_games), 10)
        self.assertTrue(all(not child.dead for child in self.backend.children))
        self.now += 600
        self.rotation.tick()
        self.assertEqual(len(self.backend.children), 10, "Same full cohort must not restart")
        self.rotation.stop()
        self.assertFalse(self.rotation.active)
        self.assertTrue(all(child.dead for child in self.backend.children))

    def test_concurrency_cap_and_fewer_selected_no_duplicates(self):
        for concurrency in (0, -1, 11, True, 1.5, "10"):
            with self.assertRaises(ValueError):
                self.rotation.start(self.many_games(10), 1, concurrency)
        games = self.many_games(3)
        self.rotation.start(games + games, 1, 10)
        self.assertEqual(len(self.rotation.current_games), 3)
        self.now += 120
        self.rotation.tick()
        self.assertEqual(len(self.backend.children), 3)

    def test_batch_boundary_last_smaller_cohort_and_wrap(self):
        self.rotation.start(self.many_games(5), 1, 3)
        self.assertEqual([game.id for game in self.rotation.current_games], ["0", "1", "2"])
        self.now += 59.9
        self.rotation.tick()
        self.assertEqual(len(self.backend.children), 3)
        self.now += .1
        self.rotation.tick()
        self.assertEqual([game.id for game in self.rotation.current_games], ["3", "4"])
        self.assertTrue(all(child.dead for child in self.backend.children[:3]))
        self.now += 60
        self.rotation.tick()
        self.assertEqual([game.id for game in self.rotation.current_games], ["0", "1", "2"])
        self.assertTrue(all(child.dead for child in self.backend.children[3:5]))

    def test_basename_collision_rejected_explicitly(self):
        games = [Game("1", "First", "a/GAME.exe"), Game("2", "Second", "b/game.exe")]
        with self.assertRaisesRegex(ValueError, "First.*Second"):
            self.rotation.start(games, 1, 2)
        self.assertEqual(self.backend.events, [])
        self.rotation.start(games, 1, 1)  # Sequential mode remains available.

    def test_nth_start_failure_rolls_back_every_started_child(self):
        self.backend.fail_at = 5
        with self.assertRaises(OSError):
            self.rotation.start(self.many_games(10), 1, 10)
        self.assertEqual(len(self.backend.children), 4)
        self.assertTrue(all(child.dead for child in self.backend.children))
        self.assertFalse(self.rotation.active)
        self.assertFalse(self.rotation.running)

    def test_partial_rotation_launch_failure_rolls_back_new_cohort(self):
        self.rotation.start(self.many_games(6), 1, 3)
        self.backend.fail_at = 5
        self.now += 60
        with self.assertRaises(OSError):
            self.rotation.tick()
        self.assertTrue(all(child.dead for child in self.backend.children))
        self.assertFalse(self.rotation.active)
        self.assertFalse(self.rotation.running)

    def test_failed_stop_keeps_only_failed_handles_for_retry(self):
        self.rotation.start(self.many_games(3), 1, 3)
        self.backend.stop_fail_ids = {"1"}
        with self.assertRaisesRegex(RuntimeError, "Game 1"):
            self.rotation.stop()
        self.assertEqual([game.id for game in self.rotation.current_games], ["1"])
        self.assertFalse(self.rotation.running)
        self.assertTrue(self.rotation.active)
        self.assertTrue(self.backend.children[0].dead)
        self.assertTrue(self.backend.children[2].dead)
        self.now += 120
        self.rotation.tick()
        self.assertEqual(len(self.backend.children), 3, "No launches after cleanup error")
        self.backend.stop_fail_ids.clear()
        self.rotation.stop()
        self.assertFalse(self.rotation.active)

    def test_start_rollback_stop_failure_retains_ownership(self):
        self.backend.fail_at = 3
        self.backend.stop_fail_ids = {"0"}
        with self.assertRaisesRegex(RuntimeError, "Game 0"):
            self.rotation.start(self.many_games(5), 1, 5)
        self.assertEqual([game.id for game in self.rotation.current_games], ["0"])
        self.assertTrue(self.backend.children[1].dead)
        self.assertFalse(self.rotation.running)
        with self.assertRaises(ValueError):
            self.rotation.start(self.many_games(1), 1)
        self.backend.stop_fail_ids.clear()
        self.rotation.stop()
        self.assertFalse(self.rotation.active)

    def test_rotation_stop_failure_launches_no_new_cohort(self):
        self.rotation.start(self.many_games(4), 1, 2)
        self.backend.stop_fail_ids = {"0"}
        self.now += 60
        with self.assertRaises(RuntimeError):
            self.rotation.tick()
        self.assertEqual(len(self.backend.children), 2)
        self.assertFalse(self.rotation.running)
        self.assertEqual([game.id for game in self.rotation.current_games], ["0"])

    def test_one_unexpected_exit_cleans_all_other_members(self):
        self.rotation.start(self.many_games(10), 1, 10)
        self.backend.children[4].dead = True
        with self.assertRaises(RuntimeError):
            self.rotation.tick()
        self.assertTrue(all(child.dead for child in self.backend.children))
        self.assertFalse(self.rotation.active)
        self.assertFalse(self.rotation.running)

    def test_unexpected_exit_and_stop_failure_retains_remaining_member(self):
        self.rotation.start(self.many_games(3), 1, 3)
        self.backend.children[0].dead = True
        self.backend.stop_fail_ids = {"2"}
        with self.assertRaisesRegex(RuntimeError, "Game 2"):
            self.rotation.tick()
        self.assertEqual([game.id for game in self.rotation.current_games], ["2"])
        self.assertTrue(self.backend.children[1].dead)
        self.assertFalse(self.rotation.running)

    def test_poll_error_stops_every_child_and_retains_unknown_handle(self):
        self.rotation.start(self.many_games(3), 1, 3)
        with patch.object(self.backend.children[0], "poll", side_effect=OSError("poll failed")):
            with self.assertRaisesRegex(RuntimeError, "poll failed"):
                self.rotation.tick()
        self.assertTrue(all(child.dead for child in self.backend.children))
        self.assertFalse(self.rotation.running)
        self.assertEqual([game.id for game in self.rotation.current_games], ["0"])
        self.rotation.stop()
        self.assertFalse(self.rotation.active)


class ConflictFilterTests(unittest.TestCase):
    def test_first_preserved_case_insensitive_nested_paths(self):
        first = Game("1", "First", "folder/GAME.exe")
        unique = Game("2", "Unique", "other.exe")
        later = Game("3", "Later", "different/path/game.EXE")
        last = Game("4", "Last", "deep/OTHER.EXE")
        source = [first, unique, later, last]
        kept, removed = filter_conflicting_games(source)
        self.assertEqual(kept, [first, unique])
        self.assertEqual(removed, [later, last])
        self.assertEqual(source, [first, unique, later, last], "Pure filter must not mutate input")
        rotation = Rotation(FakeBackend())
        rotation.start(kept, 1, 10)
        self.assertEqual(rotation.current_games, kept)
        rotation.stop()

    def test_empty_and_unique_unchanged(self):
        self.assertEqual(filter_conflicting_games([]), ([], []))
        unique = [Game("1", "A", "a.exe"), Game("2", "B", "b.exe")]
        self.assertEqual(filter_conflicting_games(unique), (unique, []))

    def test_invalid_path_is_reported_instead_of_silently_removed(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            filter_conflicting_games([Game("1", "Valid", "game.exe"), Game("2", "Invalid", "../game.exe")])

    def fake_app(self, selected, active=False):
        from app import App
        instance = App.__new__(App)
        instance.rotation = SimpleNamespace(active=active, running=False)
        instance.selected = {game.id: game for game in selected}
        instance.status = Mock()
        instance.redraw_queue = Mock()
        instance.root = object()
        return instance

    def test_gui_active_including_rollback_prevents_queue_mutation(self):
        games = [Game("1", "A", "game.exe"), Game("2", "B", "GAME.exe")]
        instance = self.fake_app(games, active=True)
        with patch("app.messagebox.showinfo") as dialog:
            instance.filter_conflicts()
        self.assertEqual(list(instance.selected.values()), games)
        instance.redraw_queue.assert_not_called()
        dialog.assert_not_called()

    def test_gui_filters_explicitly_and_bounds_large_dialog(self):
        games = [Game(str(i), f"Game {i}", "game.exe") for i in range(1000)]
        instance = self.fake_app(games)
        with patch("app.messagebox.showinfo") as dialog:
            instance.filter_conflicts()
        self.assertEqual(list(instance.selected.values()), games[:1])
        self.assertIn("999", instance.status.set.call_args.args[0])
        text = dialog.call_args.args[1]
        self.assertIn("Game 1", text)
        self.assertIn("989", text)
        self.assertNotIn("Game 999", text)
        self.assertLess(len(text), 1500)

    def test_gui_invalid_path_leaves_entire_queue_unchanged(self):
        games = [Game("1", "A", "game.exe"), Game("2", "B", "game.exe"), Game("3", "Invalid", "../game.exe")]
        instance = self.fake_app(games)
        instance.filter_conflicts()
        self.assertEqual(list(instance.selected.values()), games)
        self.assertIn("Invalid", instance.status.set.call_args.args[0])
        instance.redraw_queue.assert_not_called()

    def test_gui_button_disabled_until_all_handles_stopped(self):
        instance = self.fake_app([])
        for name in ("start_button", "stop_button", "concurrency_input", "minutes_input", "filter_conflicts_button"):
            setattr(instance, name, Mock())
        instance.set_running(True)
        instance.filter_conflicts_button.configure.assert_called_with(state="disabled")
        instance.set_running(False)
        instance.filter_conflicts_button.configure.assert_called_with(state="normal")


@unittest.skipUnless(os.name == "nt", "Windows helper")
class HelperTests(unittest.TestCase):
    @staticmethod
    def visible_windows(pid):
        user32 = ctypes.windll.user32
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        found = []
        def visit(hwnd, _):
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and user32.IsWindowVisible(hwnd):
                text = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, text, len(text))
                found.append((hwnd, text.value))
            return True
        callback = callback_type(visit)
        user32.EnumWindows(callback, 0)
        return found

    def test_fresh_localappdata_cache_and_reported_games(self):
        # Reproduces packaged Windows filesystem redirection: before creation,
        # LOCALAPPDATA resolves to an alias; after mkdir it resolves to LocalCache.
        base = Path(os.environ["LOCALAPPDATA"])
        cache = base / ("DiscordGameIdler-test-" + uuid.uuid4().hex)
        before = cache.resolve()
        try:
            backend = ProcessBackend(cache)
            self.assertEqual(backend.cache, cache.resolve(strict=True))
            self.assertTrue(backend.cache.is_dir())
            games = read_catalog(Path(__file__).with_name("catalog.json"))
            reported = [game for game in games if game.name.casefold() in {"only up!", "onebit adventure"}]
            self.assertEqual(len(reported), 2)
            print(f"\nFresh cache resolution: {before} -> {backend.cache}")
            for game in reported:
                child = backend.start(game)
                try:
                    time.sleep(.2)
                    self.assertIsNone(child.poll())
                    print(f"Start/stop smoke: {game.name} ({game.executable})")
                finally:
                    backend.stop(child)
                self.assertIsNotNone(child.poll())
        finally:
            resolved = cache.resolve()
            # Only remove this test's generated directory inside LOCALAPPDATA.
            if resolved.exists() and resolved.is_relative_to(base.resolve()) and resolved.name == cache.name:
                shutil.rmtree(resolved)

    def test_real_helper_start_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = ProcessBackend(Path(directory))
            child = backend.start(Game("1", "Smoke test", "nested/codex-idler-smoke.exe"))
            try:
                deadline = time.monotonic() + 5
                windows = []
                while not windows and time.monotonic() < deadline:
                    time.sleep(.1)
                    windows = self.visible_windows(child.pid)
                self.assertIsNone(child.poll())
                self.assertTrue(windows, "Helper must own a real visible top-level window")
                self.assertTrue(any(title == "Smoke test — имитация" for _, title in windows))
            finally:
                backend.stop(child)
            self.assertIsNotNone(child.poll())

    def test_ten_real_helpers_have_windows_and_all_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = ProcessBackend(Path(directory))
            rotation = Rotation(backend)
            games = [Game(str(i), f"Concurrency smoke {i}", f"codex-idler-smoke-{i}.exe") for i in range(10)]
            try:
                rotation.start(games, 1, 10)
                children = [process for game, process in rotation.processes]
                self.assertEqual(len(children), 10)
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if all(self.visible_windows(child.pid) for child in children):
                        break
                    time.sleep(.1)
                self.assertTrue(all(child.poll() is None for child in children))
                self.assertTrue(all(self.visible_windows(child.pid) for child in children))
            finally:
                rotation.stop()
            self.assertTrue(all(child.poll() is not None for child in children))

    def test_parent_death_stops_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = ProcessBackend(Path(directory))
            helper = backend.compile_helper()
            backend.update_language()
            parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2)"], creationflags=subprocess.CREATE_NO_WINDOW)
            child = subprocess.Popen([str(helper), str(parent.pid), "Parent lifecycle test", str(backend.helper_language_path)], creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                self.assertIsNone(child.poll())
                parent.wait(timeout=5)
                self.assertEqual(child.wait(timeout=5), 0)
            finally:
                if parent.poll() is None:
                    parent.kill()
                    parent.wait()
                if child.poll() is None:
                    child.kill()
                    child.wait()

    def test_cache_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = ProcessBackend(Path(directory))
            with self.assertRaises(ValueError):
                backend.start(Game("1", "Bad", "../../bad.exe"))


if __name__ == "__main__":
    unittest.main()
