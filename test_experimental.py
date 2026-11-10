import queue
import threading
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from app import App
from core import Game, Rotation
from i18n import UserValueError, UserRuntimeError, current_language, set_language, tr
from test_core import FakeBackend


def games(count):
    return [Game(str(i), f"Game {i}", f"game-{i}.exe") for i in range(count)]


class ExperimentalTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.backend = FakeBackend()
        self.cancel = threading.Event()
        self.rotation = Rotation(self.backend, lambda: self.now, self.cancel)

    def test_four_independent_flag_combinations_and_user_examples(self):
        for many, timed, count, expected in ((False, False, 10, 10800),
                                             (True, False, 100, 10800),
                                             (False, True, 1, 10),
                                             (True, True, 100, 10)):
            with self.subTest(many=many, timed=timed):
                backend = FakeBackend()
                rotation = Rotation(backend, lambda: self.now)
                rotation.start(games(101), 180, count, experimental_concurrency=many,
                               experimental_timing=timed, seconds=10)
                self.assertEqual(rotation.interval, expected)
                self.assertEqual(len(rotation.current_games), count)
                self.now = rotation.changed + expected - .01
                rotation.tick()
                self.assertEqual(rotation.index, 0)
                self.now = rotation.changed + expected
                rotation.tick()
                self.assertEqual(rotation.current_games[0].id, str(count))
                rotation.stop()

    def test_active_unit_validation_and_inactive_input_ignored(self):
        for seconds in (10, 86400):
            self.rotation.start(games(2), None, 1, experimental_timing=True, seconds=seconds)
            self.assertEqual(self.rotation.interval, seconds)
            self.rotation.stop()
        for minutes in (1, 1440):
            self.rotation.start(games(2), minutes, 1, seconds=None)
            self.assertEqual(self.rotation.interval, minutes * 60)
            self.rotation.stop()
        for minutes in (True, None, "180", float("nan"), float("inf"), .99, 1440.01):
            with self.assertRaises(UserValueError):
                self.rotation.start(games(2), minutes, 1, experimental_concurrency=True)
        with self.assertRaises(UserValueError):
            self.rotation.start(games(100), 180, 100, experimental_timing=True)

    def test_explicit_mode_and_caps(self):
        for flag in ("experimental_concurrency", "experimental_timing"):
            for mode in (1, 0, "yes", None):
                with self.assertRaises(UserValueError):
                    self.rotation.start(games(100), 1, 1, **{flag: mode})
        for count in (100, 11):
            with self.assertRaises(UserValueError):
                self.rotation.start(games(100), 1, count)
        for count in (101, 0, True, 100.0, "100"):
            with self.assertRaises(UserValueError):
                self.rotation.start(games(100), 1, count, experimental_concurrency=True)
        for seconds in (True, None, "10", float("nan"), float("inf"), 9.99, 86401):
            with self.assertRaises(UserValueError):
                self.rotation.start(games(100), 1, 100, experimental_concurrency=True,
                                    experimental_timing=True, seconds=seconds)
        self.rotation.start(games(100), 15, 100, experimental_concurrency=True, experimental_timing=True)
        self.assertEqual(len(self.rotation.current_games), 100)
        self.assertEqual(self.rotation.interval, 10)
        self.rotation.stop()
        self.assertTrue(all(child.dead for child in self.backend.children))

    def test_ten_second_boundary_remainder_and_no_overlap(self):
        self.rotation.start(games(105), 15, 100, experimental_concurrency=True, experimental_timing=True)
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
        self.rotation.start(games(103), 1, 100, experimental_concurrency=True, experimental_timing=True)
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
        self.rotation.start(selected + selected, 1, 100, experimental_concurrency=True, experimental_timing=True)
        self.now += 100
        self.rotation.tick()
        self.assertEqual(self.rotation.current_games, selected)
        self.assertEqual(len(self.backend.children), 3)
        self.rotation.stop()

    def test_late_failure_rolls_back_all_earlier_children(self):
        self.backend.fail_at = 99
        with self.assertRaises(OSError):
            self.rotation.start(games(100), 1, 100, experimental_concurrency=True, experimental_timing=True)
        self.assertEqual(len(self.backend.children), 98)
        self.assertTrue(all(child.dead for child in self.backend.children))
        self.assertFalse(self.rotation.active)
        self.assertFalse(self.rotation.running)

    def test_partial_rotation_failure_and_failed_cleanup_keep_handle(self):
        self.rotation.start(games(105), 1, 100, experimental_concurrency=True, experimental_timing=True)
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
            self.rotation.start(games(100), 1, 100, experimental_concurrency=True, experimental_timing=True)
        self.assertEqual(caught.exception.key, "error.cancelled")
        self.assertTrue(all(child.dead for child in self.backend.children))
        self.assertFalse(self.rotation.active)

    def test_cancel_during_old_group_stop_launches_no_next_group(self):
        self.rotation.start(games(105), 1, 100, experimental_concurrency=True, experimental_timing=True)
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
        app.super_experimental = Mock()
        app.super_experimental.get.return_value = False
        for name in ("start_button", "stop_button", "concurrency_input", "minutes_input", "filter_conflicts_button", "count_experiment_input", "time_experiment_input", "super_experiment_input", "super_warning", "language_input"):
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
        app.run_operation("start", lambda: rotation.start(games(100), 1, 100, experimental_concurrency=True, experimental_timing=True))
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
        rotation.start(games(2), 1, 2, experimental_concurrency=True, experimental_timing=True)
        backend.stop_fail_ids = {"0"}
        with self.assertRaises(UserRuntimeError):
            rotation.stop()
        app = self.fake_app(rotation, threading.Event())
        app.experimental_concurrency, app.experimental_timing = Mock(), Mock()
        app.change_concurrency_mode()
        app.change_timing_mode()
        app.experimental_concurrency.set.assert_called_once_with(True)
        app.experimental_timing.set.assert_called_once_with(True)
        backend.stop_fail_ids.clear()
        rotation.stop()

    def test_independent_toggle_preserves_other_values_and_busy_guard(self):
        app = self.fake_app(Rotation(FakeBackend()), threading.Event())
        app.experimental_concurrency, app.experimental_timing = Mock(), Mock()
        app.concurrency, app.minutes, app.seconds, app.apply_modes = Mock(), Mock(), Mock(), Mock()
        app.experimental_concurrency.get.return_value = True
        app.change_concurrency_mode()
        app.concurrency.set.assert_not_called()  # Enabling the cap never forces 100.
        app.experimental_timing.set.assert_not_called()
        app.minutes.set.assert_not_called()
        app.seconds.set.assert_not_called()
        app.concurrency.get.return_value = "100"
        app.experimental_concurrency.get.return_value = False
        app.change_concurrency_mode()
        app.concurrency.set.assert_called_once_with("10")
        app.change_timing_mode()
        app.experimental_concurrency.set.assert_not_called()
        app.minutes.set.assert_not_called()
        app.seconds.set.assert_not_called()
        app._operation_busy = True
        app.change_concurrency_mode()
        app.change_timing_mode()
        self.assertEqual(app.apply_modes.call_count, 3)

    def test_time_toggle_restores_separate_minutes_and_seconds_inputs(self):
        app = self.fake_app(Rotation(FakeBackend()), threading.Event())
        for name in ("experimental_concurrency", "experimental_timing", "concurrency", "minutes", "seconds", "max_note", "time_unit"):
            setattr(app, name, Mock())
        app.experimental_concurrency.get.return_value = True
        app.minutes.get.return_value = "180"
        app.seconds.get.return_value = "10"
        app.experimental_timing.get.return_value = True
        app.change_timing_mode()
        self.assertIs(app.minutes_input.configure.call_args.kwargs["textvariable"], app.seconds)
        self.assertEqual(app.minutes_input.configure.call_args.kwargs["from_"], 10)
        app.experimental_timing.get.return_value = False
        app.change_timing_mode()
        self.assertIs(app.minutes_input.configure.call_args.kwargs["textvariable"], app.minutes)
        self.assertEqual(app.minutes_input.configure.call_args.kwargs["to"], 1440)
        app.minutes.set.assert_not_called()
        app.seconds.set.assert_not_called()
        app.experimental_concurrency.set.assert_not_called()
        app.concurrency.set.assert_not_called()

    def test_seconds_start_ignores_invalid_hidden_minutes_and_count_experiment(self):
        rotation = Rotation(FakeBackend())
        app = self.fake_app(rotation, threading.Event())
        app.experimental_concurrency, app.experimental_timing = Mock(), Mock()
        app.experimental_concurrency.get.return_value = False
        app.experimental_timing.get.return_value = True
        app.concurrency, app.minutes, app.seconds = Mock(), Mock(), Mock()
        app.concurrency.get.return_value, app.minutes.get.return_value, app.seconds.get.return_value = "1", "invalid", "10"
        app.selected = {game.id: game for game in games(3)}
        app.run_operation = Mock()
        app.start()
        app.run_operation.call_args.args[1]()
        self.assertEqual(rotation.concurrency, 1)
        self.assertEqual(rotation.interval, 10)
        self.assertFalse(rotation.experimental_concurrency)
        self.assertTrue(rotation.experimental_timing)
        app.minutes.get.assert_not_called()
        rotation.stop()

    def test_all_experiment_controls_disabled_during_operations(self):
        app = self.fake_app(Rotation(FakeBackend()), threading.Event())
        app.set_running(True)
        app.count_experiment_input.configure.assert_called_with(state="disabled")
        app.time_experiment_input.configure.assert_called_with(state="disabled")
        app.super_experiment_input.configure.assert_called_with(state="disabled")
        app.set_running(False)
        app.count_experiment_input.configure.assert_called_with(state="normal")
        app.time_experiment_input.configure.assert_called_with(state="normal")
        app.super_experiment_input.configure.assert_called_with(state="normal")

    def test_super_start_passes_opt_in_and_preserves_minutes(self):
        rotation = Rotation(FakeBackend())
        rotation.start = Mock()
        app = self.fake_app(rotation, threading.Event())
        app.experimental_concurrency, app.experimental_timing = Mock(), Mock()
        app.experimental_concurrency.get.return_value = True
        app.experimental_timing.get.return_value = False
        app.super_experimental.get.return_value = True
        app.concurrency, app.minutes = Mock(), Mock()
        app.concurrency.get.return_value, app.minutes.get.return_value = "1000", "180"
        app.selected = {game.id: game for game in games(3)}
        app.run_operation = Mock()
        app.start()
        app.run_operation.call_args.args[1]()
        rotation.start.assert_called_once_with(games(3), 180.0, 1000, experimental_concurrency=True,
                                              experimental_timing=False, seconds=10.0, super_experimental=True)

    @unittest.skipUnless(os.name == "nt", "Windows Tk layout")
    def test_super_control_unlocks_and_clamps_without_changing_timing(self):
        import tkinter as tk
        previous = current_language()
        with tempfile.TemporaryDirectory() as directory:
            with patch("app.cache_directory", return_value=Path(directory)):
                root = tk.Tk()
                root.withdraw()
                try:
                    app = App(root)
                    self.assertFalse(app.super_experiment_input.winfo_manager())
                    self.assertEqual(app.count_limit(), 10)
                    app.experimental_timing.set(True)
                    app.minutes.set("180")
                    app.seconds.set("25")
                    app.change_timing_mode()
                    app.experimental_concurrency.set(True)
                    app.change_concurrency_mode()
                    self.assertEqual(app.super_experiment_input.winfo_manager(), "grid")
                    self.assertEqual(app.count_limit(), 100)
                    app.super_experimental.set(True)
                    app.change_super_mode()
                    self.assertEqual(app.count_limit(), 1000)
                    for language in ("ru", "en"):
                        set_language(language)
                        app.render_language()
                        root.update_idletasks()
                        self.assertEqual(app.super_warning.cget("text"), tr("app.super_warning"))
                        self.assertLessEqual(app.super_experiment_input.master.winfo_reqwidth(), 760)
                    app.concurrency.set("1000")
                    app.super_experimental.set(False)
                    app.change_super_mode()
                    self.assertEqual(app.concurrency.get(), "100")
                    app.super_experimental.set(True)
                    app.change_super_mode()
                    app.experimental_concurrency.set(False)
                    app.change_concurrency_mode()
                    self.assertFalse(app.super_experimental.get())
                    self.assertFalse(app.super_warning.winfo_manager())
                    self.assertEqual(app.concurrency.get(), "10")
                    self.assertTrue(app.experimental_timing.get())
                    self.assertEqual((app.minutes.get(), app.seconds.get()), ("180", "25"))
                    self.assertFalse(app.rotation.active)
                finally:
                    root.destroy()
                    set_language(previous)

    @unittest.skipUnless(os.name == "nt", "Windows Tk layout")
    def test_bilingual_adjacent_warnings_fit_minimum_width_without_activity(self):
        import tkinter as tk
        previous = current_language()
        with tempfile.TemporaryDirectory() as directory:
            with patch("app.cache_directory", return_value=Path(directory)):
                root = tk.Tk()
                root.withdraw()
                try:
                    app = App(root)
                    self.assertFalse(app.experimental_concurrency.get())
                    self.assertFalse(app.experimental_timing.get())
                    for language in ("ru", "en"):
                        set_language(language)
                        app.render_language()
                        for _ in range(3):
                            root.update_idletasks()
                        for name in ("count", "time"):
                            checkbox = getattr(app, name + "_experiment_input")
                            warning = getattr(app, name + "_warning")
                            self.assertIs(checkbox.master, warning.master)
                            self.assertEqual(warning.cget("text"), tr("app.performance_warning"))
                            self.assertLessEqual(checkbox.master.winfo_reqwidth(), 760)
                    self.assertFalse(app.rotation.active)
                finally:
                    root.destroy()
                    set_language(previous)

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
        app.experimental_concurrency, app.experimental_timing, app.concurrency = Mock(), Mock(), Mock()
        app.experimental_concurrency.get.return_value = True
        app.experimental_timing.get.return_value = True
        app.seconds = Mock()
        app.seconds.get.return_value = "10"
        app.concurrency.get.return_value = "not an integer"
        with patch("app.messagebox.showerror") as dialog:
            app.start()
        self.assertIn("100", dialog.call_args.args[1])
        self.assertFalse(app._operation_busy)


if __name__ == "__main__":
    unittest.main()
