import json
import os
from pathlib import Path
import string
import tempfile
import time
import unittest
from unittest.mock import Mock

from app import App
from core import Game, ProcessBackend, Rotation, executable_conflict_key
from i18n import (STRINGS, Message, UserValueError, UserRuntimeError, current_language,
                  load_language, save_language, set_language, tr)
from test_core import FakeBackend
import test_core


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.previous = current_language()

    def tearDown(self):
        set_language(self.previous)

    def test_catalog_key_and_placeholder_parity(self):
        self.assertEqual(set(STRINGS["ru"]), set(STRINGS["en"]))
        formatter = string.Formatter()
        for key, ru in STRINGS["ru"].items():
            en = STRINGS["en"][key]
            fields = lambda text: {field for _, field, _, _ in formatter.parse(text) if field is not None}
            self.assertEqual(fields(ru), fields(en), key)
            self.assertTrue(ru.strip() and en.strip(), key)

    def test_requested_performance_warning_is_translated(self):
        set_language("ru")
        self.assertEqual(tr("app.performance_warning"), "Может снизить производительность системы")
        set_language("en")
        self.assertEqual(tr("app.performance_warning"), "May reduce system performance")

    def test_dynamic_error_and_nested_message_translate_after_creation(self):
        set_language("ru")
        with self.assertRaises(UserValueError) as captured:
            executable_conflict_key(Game("1", "My game", "../bad.exe"))
        error = captured.exception
        message = Message("status.unchanged", error=error)
        self.assertIn("Недопустимый", str(message))
        set_language("en")
        self.assertIn("Invalid game path: My game", str(message))
        self.assertIn("Queue unchanged", str(message))
        self.assertNotIn("Недопустимый", str(message))

    def test_nested_cleanup_error_keeps_language_semantics(self):
        backend = FakeBackend()
        rotation = Rotation(backend)
        backend.fail_at = 2
        backend.stop_fail_ids = {"1"}
        set_language("ru")
        with self.assertRaises(UserRuntimeError) as captured:
            rotation.start([Game("1", "First", "a.exe"), Game("2", "Second", "b.exe")], 1, 2)
        set_language("en")
        self.assertIn("Could not start the group", str(captured.exception))
        self.assertIn("Click Stop again", str(captured.exception))
        backend.stop_fail_ids.clear()
        rotation.stop()

    def test_preference_round_trip_missing_invalid_and_large_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            self.assertEqual(load_language(path, "en"), "en")
            for language in ("en", "ru"):
                save_language(path, language)
                self.assertEqual(load_language(path, "en"), language)
            for content in ('{"language":"zz"}', '[]', '{bad', '{"language":[]}', '"en"'):
                path.write_text(content, encoding="utf-8")
                self.assertEqual(load_language(path, "ru"), "ru")
            path.write_text(" " * 5000, encoding="utf-8")
            self.assertEqual(load_language(path, "en"), "en")
            with self.assertRaises(ValueError):
                save_language(path, "zz")

    def test_live_app_change_preserves_session_queue_and_local_time(self):
        set_language("ru")
        game = Game("1", "Preserved game", "a.exe")
        backend = FakeBackend()
        backend.update_language = Mock()
        rotation = Rotation(backend)
        rotation.start([game], 1)
        child = rotation.process
        rotation.elapsed = 123
        app = App.__new__(App)
        app.rotation = rotation
        app.selected = {game.id: game}
        app.language = Mock()
        app.language.get.return_value = "English"
        app.root, app.tree, app.status = Mock(), Mock(), Mock()
        app._text_widgets = [(Mock(), "app.start")]
        app._message_specs = {}
        app.set_message(app.status, "status.filtered", removed=2, kept=1)
        with tempfile.TemporaryDirectory() as directory:
            app.preferences_path = Path(directory) / "settings.json"
            app.change_language()
            self.assertEqual(load_language(app.preferences_path), "en")
        self.assertEqual(current_language(), "en")
        self.assertIs(rotation.process, child)
        self.assertEqual(rotation.elapsed, 123)
        self.assertEqual(app.selected, {game.id: game})
        self.assertEqual(len(backend.children), 1)
        self.assertIn("Removed conflicting games", app.status.set.call_args.args[0])
        backend.update_language.assert_called_once()
        rotation.stop()

    @unittest.skipUnless(os.name == "nt", "Windows helper")
    def test_live_helper_language_change_keeps_same_process(self):
        set_language("ru")
        with tempfile.TemporaryDirectory() as directory:
            backend = ProcessBackend(Path(directory))
            child = backend.start(Game("1", "Language smoke", "codex-language-smoke.exe"))
            def wait_title(title):
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if any(text == title for _, text in test_core.HelperTests.visible_windows(child.pid)):
                        return True
                    time.sleep(.1)
                return False
            try:
                self.assertTrue(wait_title("Language smoke — имитация"))
                set_language("en")
                backend.update_language()
                self.assertTrue(wait_title("Language smoke — simulation"))
                self.assertIn(tr("helper.body"), backend.helper_language_path.read_text(encoding="utf-8"))
                self.assertIsNone(child.poll())
            finally:
                backend.stop(child)


if __name__ == "__main__":
    unittest.main()
