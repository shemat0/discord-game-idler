"""Runtime translations and small, validated local language preferences."""
from __future__ import annotations
import ctypes
import json
import locale
import os
import threading
from pathlib import Path

STRINGS = {
    "en": {
        "app.experiment_super": "Super experiment: up to 1000",
        "app.super_warning": "May work incorrectly with your system and use more than 1 GB of RAM.",
        "app.performance_title": "Experimental mode",
        "app.performance_details": "This mode can increase system load and slow down your computer.",
        "app.super_title": "Enable the super experiment",
        "app.acknowledge_risks": "I understand the risks",
        "app.cancel": "Cancel",
        "app.enable": "Enable",
        "app.queue_count": "Game queue: {count}",
        "app.theme": "Theme",
        "theme.dark": "Dark", "theme.light": "Light",
        "status.theme_error": "Theme changed, but settings or helper appearance could not be saved: {error}",
        "app.experiment_count": "Experiment: up to 100",
        "app.experiment_time": "Experiment: seconds",
        "app.performance_warning": "May reduce system performance",
        "app.count_range": "(1–{limit})",
        "app.unit_minutes": "minutes",
        "app.unit_seconds": "seconds",
        "error.seconds_interval": "Select games and an interval between 10 and 86400 seconds.",
        "error.input_parameters": "Enter a whole game count from 1 to {limit} and a numeric interval in {unit}.",
        "app.clear_queue": "Clear queue",
        "status.queue_cleared": "Queue cleared. Add games from the catalog to begin again.",
        "status.starting": "Starting processes… Stop cancels after the current launch step.",
        "status.stopping": "Stopping processes… Please wait for cleanup.",
        "error.mode": "Experimental mode must be explicitly enabled or disabled.",
        "error.concurrent_limit": "Concurrent game count must be between 1 and {limit}.",
        "error.cancelled": "Launch cancelled. Cleaning up processes.",
        "app.title": "Discord Game Idler",
        "app.heading": "Game session",
        "app.subtitle": "Experimental game-process simulation for Discord desktop",
        "app.intro": "Badge credit is unconfirmed. Time passes in real time.\nDiscord requires data personalization for these badges.",
        "app.refresh": "Update catalog", "app.game": "Game", "app.process": "Process",
        "app.queue": "Game queue", "app.add": "Add selected →", "app.remove": "Remove from queue",
        "app.filter": "Remove conflicts", "app.concurrent": "At the same time:",
        "app.max": "games (maximum 10)", "app.start": "▶ Start", "app.stop": "■ Stop",
        "app.interval": "Rotate group every", "app.minutes": "minutes • a queue that fits stays running",
        "app.timer_note": "This is a local session timer. Discord detection and playtime credit for every concurrent game are unconfirmed.",
        "status.initial": "Load the game catalog to begin.", "status.choose": "Select games and add them to the queue.",
        "status.choose_one": "Add games to the queue. Start with one game to check detection.",
        "status.cache_error": "Could not read the cached catalog: {error}",
        "status.catalog_error": "Catalog error: {error}. You can retry later.",
        "status.empty": "The queue is empty. Add games from the catalog.",
        "status.unchanged": "Queue unchanged: {error}", "status.no_conflicts": "No conflicts. Games in queue: {count}.",
        "status.filtered": "Removed conflicting games: {removed}. Remaining: {kept}. The first game for each EXE name was kept.",
        "status.running": "Simulation windows are open; you may minimize them. Closing any window stops the group. Check detection in Discord; credit for all games is unconfirmed.",
        "status.start_error": "Start error: {error}", "status.stop_error": "Stop error: {error}",
        "status.stopped": "Session stopped. All processes created by this app have exited.",
        "status.language_error": "Language changed, but preferences or helper text could not be saved: {error}",
        "catalog.initial": "Catalog not loaded", "catalog.loading": "Downloading Discord's public catalog…",
        "catalog.cached": "Cached catalog: {count} games", "catalog.bundled": "Bundled catalog (2026-11-04): {count} games",
        "catalog.updated": "Catalog updated: {count} games", "catalog.failed": "Download failed. Available locally: {count} games",
        "session.stopped": "Session stopped", "session.running": "Running games: {count}",
        "session.pending": "Still to stop: {count}", "session.timer": "{state}  •  local time {time}",
        "dialog.filtered_title": "Conflicts removed", "dialog.filtered_body": "Removed from queue ({count}):\n{details}",
        "dialog.more": "…and {count} more.", "dialog.start_error": "Could not start",
        "dialog.close_title": "Closing", "dialog.close_error": "Some processes could not be stopped. Please retry Stop.",
        "dialog.already_open": "The app is already running. Find its window on the taskbar.",
        "error.raw": "{error}", "error.invalid_path": "Invalid game path: {name}",
        "error.catalog_schema": "Invalid Discord catalog: expected a list.",
        "error.catalog_empty": "The catalog contains no supported Windows games.",
        "error.catalog_large": "The catalog is too large.", "error.catalog_limit": "Catalog download size or time limit exceeded.",
        "error.compiler_missing": ".NET Framework 4.x compiler was not found in Windows.",
        "error.compile": "Could not build the helper process: {details}",
        "error.unsafe_path": "Unsafe game path.", "error.path_escape": "The path is outside the app's cache directory.",
        "error.active": "A session is already running.", "error.concurrency": "Concurrent game count must be between 1 and 10.",
        "error.interval": "Select games and an interval between 1 and 1440 minutes.",
        "error.numbers": "Enter a whole concurrent game count from 1 to 10 and a valid interval in minutes.",
        "error.collision": "Same process name {exe}: {first} and {second}. Remove one game, use Remove conflicts, or run one at a time.",
        "error.group_launch": "Could not start the group: {launch}. {stop}",
        "error.poll_cleanup": "Could not check processes: {error}. {stop}",
        "error.poll_stopped": "Could not check processes: {error}. The group was stopped.",
        "error.exited_cleanup": "Processes exited: {names}. {stop}",
        "error.exited_stopped": "Processes exited: {names}. All remaining processes were stopped.",
        "error.still_running": "process is still running", "error.process": "{name}: {error}",
        "error.stop": "Could not stop: {errors}. Click Stop again.",
        "helper.suffix": "simulation",
        "helper.body": "Process simulation for checking Discord.\nYou may minimize this window. Closing it stops the process.\nGame activity credit is not guaranteed.",
    },
    "ru": {
        "app.experiment_super": "Суперэксперимент: до 1000",
        "app.super_warning": "Может некорректно работать с системой и потреблять больше 1 ГБ ОЗУ.",
        "app.performance_title": "Экспериментальный режим",
        "app.performance_details": "Этот режим может увеличить нагрузку на компьютер и замедлить его работу.",
        "app.super_title": "Включение суперэксперимента",
        "app.acknowledge_risks": "Я осознаю риски",
        "app.cancel": "Отмена",
        "app.enable": "Включить",
        "app.queue_count": "Очередь игр: {count}",
        "app.theme": "Тема",
        "theme.dark": "Тёмная", "theme.light": "Светлая",
        "status.theme_error": "Тема изменена, но настройки или оформление окон не удалось сохранить: {error}",
        "app.experiment_count": "Эксперимент: до 100",
        "app.experiment_time": "Эксперимент: секунды",
        "app.performance_warning": "Может снизить производительность системы",
        "app.count_range": "(1–{limit})",
        "app.unit_minutes": "минут",
        "app.unit_seconds": "секунд",
        "error.seconds_interval": "Выберите игры и интервал от 10 до 86400 секунд.",
        "error.input_parameters": "Введите целое число игр от 1 до {limit} и числовой интервал в единицах: {unit}.",
        "app.clear_queue": "Очистить очередь",
        "status.queue_cleared": "Очередь очищена. Добавьте игры из каталога, чтобы начать заново.",
        "status.starting": "Запуск процессов… «Остановить» отменит запуск после текущего шага.",
        "status.stopping": "Остановка процессов… Дождитесь завершения очистки.",
        "error.mode": "Экспериментальный режим должен быть явно включён или выключен.",
        "error.concurrent_limit": "Число одновременно запущенных игр: от 1 до {limit}.",
        "error.cancelled": "Запуск отменён. Останавливаем созданные процессы.",
        "app.title": "Discord Game Idler", "app.heading": "Игровая сессия",
        "app.subtitle": "Экспериментальная имитация процессов для настольного Discord",
        "app.intro": "Зачёт значков не подтверждён. Часы идут в реальном времени.\nДля этих значков Discord требует включить персонализацию данных.",
        "app.refresh": "Обновить каталог", "app.game": "Игра", "app.process": "Процесс",
        "app.queue": "Очередь игр", "app.add": "Добавить выбранные →", "app.remove": "Удалить из очереди",
        "app.filter": "Убрать конфликтующие", "app.concurrent": "Одновременно:",
        "app.max": "игр (максимум 10)", "app.start": "▶ Начать", "app.stop": "■ Остановить",
        "app.interval": "Менять группу каждые", "app.minutes": "минут • если очередь помещается, игры остаются запущенными",
        "app.timer_note": "Таймер — только локальная сессия. Одновременное распознавание и начисление часов за все игры в Discord не подтверждены.",
        "status.initial": "Загрузите каталог игр для начала.", "status.choose": "Выберите игры и добавьте их в очередь.",
        "status.choose_one": "Добавьте игры в очередь. Для проверки распознавания начните с одной игры.",
        "status.cache_error": "Не удалось прочитать кэш каталога: {error}",
        "status.catalog_error": "Ошибка каталога: {error}. Можно повторить загрузку позже.",
        "status.empty": "Очередь пуста — добавьте игры из каталога.",
        "status.unchanged": "Очередь не изменена: {error}", "status.no_conflicts": "Конфликтов нет. В очереди игр: {count}.",
        "status.filtered": "Убрано конфликтующих игр: {removed}. Осталось: {kept}. Сохранена первая игра для каждого имени EXE.",
        "status.running": "Окна имитации открыты: их можно свернуть. Закрытие любого остановит группу. Проверьте распознавание в Discord; зачёт часов за все игры не подтверждён.",
        "status.start_error": "Ошибка запуска: {error}", "status.stop_error": "Ошибка остановки: {error}",
        "status.stopped": "Сессия остановлена. Все созданные приложением процессы завершены.",
        "status.language_error": "Язык изменён, но настройки или текст окон не удалось сохранить: {error}",
        "catalog.initial": "Каталог ещё не загружен", "catalog.loading": "Загружаем публичный каталог Discord…",
        "catalog.cached": "Каталог из кэша: {count} игр", "catalog.bundled": "Каталог из комплекта (04.11.2026): {count} игр",
        "catalog.updated": "Каталог обновлён: {count} игр", "catalog.failed": "Загрузка не удалась. Доступно локально: {count} игр",
        "session.stopped": "Сессия остановлена", "session.running": "Запущено игр: {count}",
        "session.pending": "Осталось остановить: {count}", "session.timer": "{state}  •  локальное время {time}",
        "dialog.filtered_title": "Конфликты убраны", "dialog.filtered_body": "Удалены из очереди ({count}):\n{details}",
        "dialog.more": "…и ещё {count}.", "dialog.start_error": "Не удалось начать",
        "dialog.close_title": "Завершение", "dialog.close_error": "Не удалось остановить все процессы. Повторите остановку.",
        "dialog.already_open": "Приложение уже запущено. Найдите его окно на панели задач.",
        "error.raw": "{error}", "error.invalid_path": "Недопустимый путь игры: {name}",
        "error.catalog_schema": "Неверный формат каталога Discord: ожидался список.",
        "error.catalog_empty": "Каталог не содержит подходящих Windows-игр.",
        "error.catalog_large": "Каталог слишком большой.", "error.catalog_limit": "Превышен размер или время загрузки каталога.",
        "error.compiler_missing": "Не найден компилятор .NET Framework 4.x в Windows.",
        "error.compile": "Не удалось собрать фоновый процесс: {details}",
        "error.unsafe_path": "Небезопасный путь игры.", "error.path_escape": "Путь выходит за папку приложения.",
        "error.active": "Сессия уже запущена.", "error.concurrency": "Число одновременно запущенных игр: от 1 до 10.",
        "error.interval": "Выберите игры и интервал от 1 до 1440 минут.",
        "error.numbers": "Введите целое число одновременно запущенных игр от 1 до 10 и корректный интервал в минутах.",
        "error.collision": "Одинаковый процесс {exe}: {first} и {second}. Уберите одну игру, нажмите «Убрать конфликтующие» или запускайте по одной.",
        "error.group_launch": "Не удалось запустить группу: {launch}. {stop}",
        "error.poll_cleanup": "Не удалось проверить процессы: {error}. {stop}",
        "error.poll_stopped": "Не удалось проверить процессы: {error}. Группа остановлена.",
        "error.exited_cleanup": "Завершились процессы: {names}. {stop}",
        "error.exited_stopped": "Завершились процессы: {names}. Все остальные остановлены.",
        "error.still_running": "процесс всё ещё запущен", "error.process": "{name}: {error}",
        "error.stop": "Не удалось остановить: {errors}. Нажмите «Остановить» ещё раз.",
        "helper.suffix": "имитация",
        "helper.body": "Имитация процесса для проверки Discord.\nОкно можно свернуть. Закрытие остановит процесс.\nЗачёт игровой активности не гарантирован.",
    },
}

_language = "ru"  # Core callers keep the historical default; the GUI loads OS/preference.


def current_language() -> str:
    return _language


def set_language(language: str) -> None:
    if language not in STRINGS:
        raise ValueError("Unsupported language")
    global _language
    _language = language


def tr(key: str, **values) -> str:
    return STRINGS[_language][key].format(**values)


class Message:
    def __init__(self, key: str, **values):
        self.key, self.values = key, values

    def __str__(self):
        return tr(self.key, **self.values)


class MessageList:
    def __init__(self, messages, separator="; "):
        self.messages, self.separator = messages, separator

    def __str__(self):
        return self.separator.join(str(message) for message in self.messages)


class UserValueError(ValueError, Message):
    def __init__(self, key, **values):
        Message.__init__(self, key, **values)
        ValueError.__init__(self, key)

    __str__ = Message.__str__


class UserRuntimeError(RuntimeError, Message):
    def __init__(self, key, **values):
        Message.__init__(self, key, **values)
        RuntimeError.__init__(self, key)

    __str__ = Message.__str__


def os_language() -> str:
    try:
        if os.name == "nt":
            # Low 10 bits are the Windows primary language identifier.
            return "ru" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x19 else "en"
        name = locale.getlocale()[0] or ""
        return "ru" if name.lower().startswith("ru") else "en"
    except (AttributeError, ValueError, OSError):
        return "en"


_preferences_lock = threading.RLock()


def read_preferences(path: Path, *, strict_io=False) -> dict:
    try:
        if path.stat().st_size > 4096:
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except OSError:
        if strict_io:
            raise
        return {}
    except (ValueError, UnicodeError):
        return {}


def load_language(path: Path, fallback: str | None = None) -> str:
    default = fallback if fallback in STRINGS else os_language()
    language = read_preferences(path).get("language")
    return language if isinstance(language, str) and language in STRINGS else default


def save_preference(path: Path, key: str, value: str) -> None:
    # Serialize read/merge/write so language and theme cannot erase each other.
    with _preferences_lock:
        preferences = read_preferences(path, strict_io=True)
        preferences[key] = value
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(preferences), encoding="utf-8")
        temporary.replace(path)


def save_language(path: Path, language: str) -> None:
    if language not in STRINGS:
        raise ValueError("Unsupported language")
    save_preference(path, "language", language)
