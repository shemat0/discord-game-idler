import queue
import threading
import unittest
from unittest.mock import Mock, patch

from app import App
from core import Game, Rotation
from i18n import UserValueError, UserRuntimeError
from test_core import FakeBackend


def games(count):
    return [Game(str(i), f"Game {i}", f"game-{i}.exe") for i in range(count)]


class ExperimentalTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.backend = FakeBackend()
        self.cancel = threading.Event()
        self.rotation = Rotation(self.backend, lambda: self.now, self.cancel)

    def test_explicit_mode_and_caps(self):
        for mode in (1, 0, "yes", None):
            with self.assertRaises(UserValueError):
                self.rotation.start(games(100), 1, 100, experimental=mode)
        for count in (100, 11):
            with self.assertRaises(UserValueError):
                self.rotation.start(games(100), 1, count)
        for count in (101, 0, True, 100.0, "100"):
            with self.assertRaises(UserValueError):
                self.rotation.start(games(100), 1, count, experimental=True)
        for minutes in (True, None, "1", float("nan"), float("inf"), 0, 1441):
            with self.assertRaises(UserValueError):
                self.rotation.start(games(100), minutes, 100, experimental=True)
        self.rotation.start(games(100), 15, 100, experimental=True)
        self.assertEqual(len(self.rotation.current_games), 100)
        self.assertEqual(self.rotation.interval, 10)
        self.rotation.stop()
        self.assertTrue(all(child.dead for child in self.backend.children))

    def test_ten_second_boundary_remainder_and_no_overlap(self):
        self.rotation.start(games(105), 15, 100, experimental=True)
        self.now = self.rotation.changed + 9.99
        self.rotation.tick()
        self.assertEqual(len(self.backend.children), 100)
        self.now = self.rotation.changed + 10
        self.rotation.tick()
        self.assertEqual([game.id for game in self.rotation.current_games], [str(i) for i in range(100, 105)])
        self.assertTrue(all(child.dead for child in self.backend.children[:100]))
        self.assertTrue(all(event[0] == "stop" for event in self.backend.events[100:200]))
        self.now += 10
        self.rotation.tick()
        self.assertEqual(len(self.rotation.current_games), 100)
        self.assertEqual(self.rotation.current_games[0].id, "0")
        self.rotation.stop()

    def test_dwell_starts_after_slow_full_cohort_launch(self):
        start = self.backend.start
        def slow_start(game):
            self.now += .25
            return start(game)
        self.backend.start = slow_start
        self.rotation.start(games(103), 1, 100, experimental=True)
        self.assertEqual(self.rotation.changed, 125)
        self.now = 134.99
        self.rotation.tick()
        self.assertEqual(len(self.backend.children), 100)
        self.now = 135
        self.rotation.tick()
        self.assertEqual(len(self.rotation.current_games), 3)
        self.assertEqual(self.rotation.changed, 135.75)
        self.now = 145.74
        self.rotation.tick()
        self.assertEqual(len(self.backend.children), 103)
        self.rotation.stop()

    def test_fitting_queue_stays_running_without_duplicate_launches(self):
        selected = games(3)
        self.rotation.start(selected + selected, 1, 100, experimental=True)
        self.now += 100
        self.rotation.tick()
        self.assertEqual(self.rotation.current_games, selected)
        self.assertEqual(len(self.backend.children), 3)
        self.rotation.stop()

    def test_late_failure_rolls_back_all_earlier_children(self):
        self.backend.fail_at = 99
        with self.assertRaises(OSError):
            self.rotation.start(games(100), 1, 100, experimental=True)
        self.assertEqual(len(self.backend.children), 98)
        self.assertTrue(all(child.dead for child in self.backend.children))
        self.assertFalse(self.rotation.active)
        self.assertFalse(self.rotation.running)

    def test_partial_rotation_failure_and_failed_cleanup_keep_handle(self):
        self.rotation.start(games(105), 1, 100, experimental=True)
        self.backend.fail_at = 105
        self.backend.stop_fail_ids = {"102"}
        self.now += 10
        with self.assertRaises(UserRuntimeError):
            self.rotation.tick()
        self.assertEqual([game.id for game in self.rotation.current_games], ["102"])
        self.assertFalse(self.rotation.running)
        self.backend.stop_fail_ids.clear()
        self.rotation.stop()
        self.assertTrue(all(child.dead for child in self.backend.children))

    def test_cancel_during_final_spawn_cleans_complete_cohort(self):
        start = self.backend.start
        def final_cancel(game):
            child = start(game)
            if len(self.backend.children) == 100:
                self.cancel.set()
            return child
        self.backend.start = final_cancel
        with self.assertRaises(UserRuntimeError) as caught:
            self.rotation.start(games(100), 1, 100, experimental=True)
        self.assertEqual(caught.exception.key, "error.cancelled")
        self.assertTrue(all(child.dead for child in self.backend.children))
        self.assertFalse(self.rotation.active)

    def test_cancel_during_old_group_stop_launches_no_next_group(self):
        self.rotation.start(games(105), 1, 100, experimental=True)
        stop = self.backend.stop
        def stop_and_cancel(child):
            self.cancel.set()
            stop(child)
        self.backend.stop = stop_and_cancel
        self.now += 10
        with self.assertRaises(UserRuntimeError):
            self.rotation.tick()
        self.assertEqual(len(self.backend.children), 100)
        self.assertTrue(all(child.dead for child in self.backend.children))
        self.assertFalse(self.rotation.active)


class OperationTests(unittest.TestCase):
    def fake_app(self, rotation, cancel):
        app = App.__new__(App)
        app.rotation, app._cancel_event = rotation, cancel
        app._operation_busy = app._stop_requested = app._closing = False
        app.messages = queue.Queue()
        app.status = Mock()
        app.root = Mock()
        for name in ("start_button", "stop_button", "concurrency_input", "minutes_input", "filter_conflicts_button", "experimental_input", "language_input"):
            setattr(app, name, Mock())
        return app

    def test_background_start_is_cancellable_without_blocking_ui(self):
        entered, release, cancel = threading.Event(), threading.Event(), threading.Event()
        backend = FakeBackend()
        start = backend.start
        def blocked_start(game):
            entered.set()
            if not release.wait(timeout=3):
                raise RuntimeError("test release timed out")
            return start(game)
        backend.start = blocked_start
        rotation = Rotation(backend, cancel_event=cancel)
        app = self.fake_app(rotation, cancel)
        app.run_operation("start", lambda: rotation.start(games(100), 1, 100, experimental=True))
        try:
            self.assertTrue(entered.wait(timeout=2))
            self.assertTrue(app._operation_busy)
            app.run_operation("start", lambda: self.fail("overlapping operation"))
            app.stop()
            self.assertTrue(cancel.is_set())
            self.assertTrue(app._stop_requested)
        finally:
            release.set()
        kind, result = app.messages.get(timeout=3)
        self.assertEqual(kind, "operation")
        app.operation_finished(*result)
        self.assertFalse(app._operation_busy)
        self.assertEqual(len(backend.children), 1)
        self.assertTrue(backend.children[0].dead)
        self.assertFalse(rotation.active)

    def test_mode_cannot_change_with_retained_processes(self):
        backend = FakeBackend()
        rotation = Rotation(backend)
        rotation.start(games(2), 1, 2, experimental=True)
        backend.stop_fail_ids = {"0"}
        with self.assertRaises(UserRuntimeError):
            rotation.stop()
        app = self.fake_app(rotation, threading.Event())
        app.experimental = Mock()
        app.change_mode()
        app.experimental.set.assert_called_once_with(True)
        backend.stop_fail_ids.clear()
        rotation.stop()

    def test_mode_toggle_uses_safe_defaults_and_busy_guard(self):
        app = self.fake_app(Rotation(FakeBackend()), threading.Event())
        app.experimental, app.concurrency, app.minutes, app.apply_mode = Mock(), Mock(), Mock(), Mock()
        app.experimental.get.return_value = True
        app.change_mode()
        app.concurrency.set.assert_called_with("100")
        app.experimental.get.return_value = False
        app.change_mode()
        app.concurrency.set.assert_called_with("10")
        app.minutes.set.assert_called_with("15")
        app._operation_busy = True
        app.change_mode()
        self.assertEqual(app.apply_mode.call_count, 2)

    def test_poll_completion_leaves_live_language_idle_window(self):
        rotation = Rotation(FakeBackend())
        rotation.start(games(1), 1)
        app = self.fake_app(rotation, threading.Event())
        app.run_operation = Mock()
        with patch("app.time.monotonic", return_value=100):
            app.operation_finished("tick", None)
            app.maybe_tick()
        app.run_operation.assert_not_called()
        app.language_input.configure.assert_called_with(state="readonly")
        with patch("app.time.monotonic", return_value=100.5):
            app.maybe_tick()
        app.run_operation.assert_called_once()
        rotation.stop()

    def test_experimental_parse_error_uses_experimental_limit(self):
        app = self.fake_app(Rotation(FakeBackend()), threading.Event())
        app.experimental, app.concurrency = Mock(), Mock()
        app.experimental.get.return_value = True
        app.concurrency.get.return_value = "not an integer"
        with patch("app.messagebox.showerror") as dialog:
            app.start()
        self.assertIn("100", dialog.call_args.args[1])
        self.assertIn("10", dialog.call_args.args[1])
        self.assertFalse(app._operation_busy)


if __name__ == "__main__":
    unittest.main()
