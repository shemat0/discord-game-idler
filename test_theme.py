import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from app import App
from core import Game, ProcessBackend, Rotation
from i18n import current_language, load_language, save_language, set_language, tr
from theme import load_theme, save_theme
from test_core import FakeBackend
import test_core


class ThemePreferenceTests(unittest.TestCase):
    def test_theme_language_cross_saves_and_invalid_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            self.assertEqual(load_theme(path), "dark")
            save_language(path, "en")
            save_theme(path, "light")
            self.assertEqual(load_language(path), "en")
            save_language(path, "ru")
            self.assertEqual(load_theme(path), "light")
            save_theme(path, "dark")
            self.assertEqual(load_language(path), "ru")
            for content in ('{bad', '[]', 'null', '{"theme":[]}', '{"theme":"unknown"}'):
                path.write_text(content, encoding="utf-8")
                self.assertEqual(load_theme(path), "dark")
            path.write_text(" " * 5000, encoding="utf-8")
            self.assertEqual(load_theme(path), "dark")

    def test_parallel_preference_updates_preserve_both_and_other_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"language": "ru", "theme": "dark", "other": "keep"}))
            gate = threading.Barrier(2)
            def language():
                gate.wait(timeout=3)
                save_language(path, "en")
            def theme():
                gate.wait(timeout=3)
                save_theme(path, "light")
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(language), executor.submit(theme)]
                for future in futures:
                    future.result(timeout=3)
            self.assertEqual(json.loads(path.read_text()), {"language": "en", "theme": "light", "other": "keep"})

    def test_unreadable_preferences_are_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"theme":"light"}')
            with patch.object(Path, "read_text", side_effect=PermissionError("read denied")):
                with self.assertRaises(PermissionError):
                    save_language(path, "en")
            self.assertEqual(path.read_text(), '{"theme":"light"}')


@unittest.skipUnless(os.name == "nt", "Windows Tk and helper")
class LiveThemeTests(unittest.TestCase):
    def setUp(self):
        self.previous_language = current_language()

    def tearDown(self):
        set_language(self.previous_language)

    def test_actual_tk_live_theme_preserves_session_queue_and_existing_popups(self):
        import tkinter as tk
        with tempfile.TemporaryDirectory() as directory:
            with patch("app.cache_directory", return_value=Path(directory)):
                root = tk.Tk()
                root.withdraw()
                try:
                    ui = App(root)
                    backend = FakeBackend()
                    backend.set_theme, backend.update_language = Mock(), Mock()
                    ui.rotation = Rotation(backend)
                    game = Game("1", "Preserved", "preserved.exe")
                    ui.rotation.start([game], 1)
                    child = ui.rotation.process
                    ui.rotation.elapsed = 123
                    ui.selected = {game.id: game}
                    ui.redraw_queue()
                    ui.set_message(ui.status, "status.running")
                    snapshots = []
                    popup = str(root.tk.call("ttk::combobox::PopdownWindow", str(ui.language_input)))
                    for language in ("ru", "en"):
                        set_language(language)
                        ui.render_language()
                        for theme in ("light", "dark"):
                            message = ui.status.get()
                            ui.theme_choice.set(tr("theme." + theme))
                            ui.change_theme()
                            for _ in range(3):
                                root.update_idletasks()
                            self.assertEqual(ui.status.get(), message)
                            self.assertEqual(ui.selected, {game.id: game})
                            self.assertIs(ui.rotation.process, child)
                            self.assertEqual(ui.rotation.elapsed, 123)
                            self.assertEqual(ui.chosen.get(0, "end"), ("Preserved",))
                            self.assertEqual(load_theme(ui.preferences_path), theme)
                            popup_color = root.tk.call(popup + ".f.l", "cget", "-background")
                            self.assertEqual(str(popup_color), ui.chosen.cget("background"))
                            snapshots.append(ui.chosen.cget("background"))
                            row = ui.theme_input.master
                            self.assertLessEqual(row.winfo_reqwidth(), 760)
                    self.assertNotEqual(snapshots[0], snapshots[1])
                    self.assertEqual(len(backend.children), 1)
                    ui.rotation.stop()
                finally:
                    root.destroy()

    def test_theme_save_error_preserves_selected_theme_and_session(self):
        ui = App.__new__(App)
        ui._operation_busy = False
        ui.theme_name = "dark"
        ui.root, ui.status, ui.theme_choice = Mock(), Mock(), Mock()
        ui.theme_choice.get.return_value = tr("theme.light")
        ui.preferences_path = Path("unused-settings.json")
        backend = FakeBackend()
        backend.set_theme = Mock()
        ui.rotation = Rotation(backend)
        ui.rotation.start([Game("1", "Preserved", "a.exe")], 1)
        child = ui.rotation.process
        with patch("app.apply_theme"), patch("app.save_theme", side_effect=PermissionError("write denied")):
            ui.change_theme()
        self.assertEqual(ui.theme_name, "light")
        self.assertIs(ui.rotation.process, child)
        self.assertIn("write denied", ui.status.set.call_args.args[0])
        ui.rotation.stop()

    def test_theme_switch_is_guarded_during_worker_operation(self):
        ui = App.__new__(App)
        ui._operation_busy = True
        ui.theme_name = "dark"
        ui.theme_choice = Mock()
        with patch("app.apply_theme") as appearance, patch("app.save_theme") as save:
            ui.change_theme()
        self.assertEqual(ui.theme_name, "dark")
        ui.theme_choice.set.assert_called_once_with(tr("theme.dark"))
        appearance.assert_not_called()
        save.assert_not_called()

    def test_live_helper_repaints_theme_without_restarting_process(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = ProcessBackend(Path(directory))
            child = backend.start(Game("1", "Theme smoke", "codex-theme-smoke.exe"))
            user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
            user32.GetDC.argtypes = [wintypes.HWND]
            user32.GetDC.restype = wintypes.HDC
            user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
            user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
            gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
            gdi32.CreateCompatibleDC.restype = wintypes.HDC
            gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
            gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
            gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
            gdi32.SelectObject.restype = wintypes.HANDLE
            gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
            gdi32.DeleteDC.argtypes = [wintypes.HDC]
            gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
            gdi32.GetPixel.restype = wintypes.DWORD
            def wait_pixel(expected):
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    windows = test_core.HelperTests.visible_windows(child.pid)
                    if windows:
                        hwnd = windows[0][0]
                        dc = user32.GetDC(hwnd)
                        memory = gdi32.CreateCompatibleDC(dc)
                        bitmap = gdi32.CreateCompatibleBitmap(dc, 460, 140)
                        previous = gdi32.SelectObject(memory, bitmap)
                        try:
                            # Render the client itself, independent of occlusion
                            # by the user's active application or other windows.
                            printed = user32.PrintWindow(hwnd, memory, 1)
                            color = gdi32.GetPixel(memory, 5, 5) if printed else -1
                        finally:
                            gdi32.SelectObject(memory, previous)
                            gdi32.DeleteObject(bitmap)
                            gdi32.DeleteDC(memory)
                            user32.ReleaseDC(hwnd, dc)
                        if color == expected:
                            return True
                    time.sleep(.1)
                return False
            try:
                self.assertTrue(wait_pixel(16 | (23 << 8) | (34 << 16)))
                backend.set_theme("light")
                self.assertTrue(wait_pixel(246 | (248 << 8) | (251 << 16)))
                backend.set_theme("dark")
                self.assertTrue(wait_pixel(16 | (23 << 8) | (34 << 16)))
                self.assertIsNone(child.poll())
            finally:
                backend.stop(child)


if __name__ == "__main__":
    unittest.main()
