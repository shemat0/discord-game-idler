# Discord Game Idler 1.1.1

Changes since the public 1.0.0 release / Изменения с публичного релиза 1.0.0

## English

- New **Clear queue** button empties the selected queue and display while idle, preserving the catalog and search. It is disabled during operations, sessions, and unfinished cleanup.
- Opt-in experimental mode (off by default): up to 100 concurrent helper processes, with group changes after 10 seconds measured from full cohort launch. Fitting queues stay running. Normal 1–10 game / 1–1440 minute mode remains available.
- Cancellable background launches and cleanup keep the UI responsive; partial groups roll back and failed stops remain tracked.
- Full Russian/English controls, statuses and errors. Helper translations allow concurrent readers during atomic text replacement.

51 existing checks plus four clear-queue checks cover this release. 100-process behavior is simulated; the real-window smoke test launches ten helpers. Discord recognition and credit for concurrent games or short sessions remain unconfirmed.

## Русский

- Новая кнопка **Очистить очередь** очищает выбранные игры и список до запуска, сохраняя каталог и поиск. Во время операций, сессии и незавершённой остановки кнопка недоступна.
- Эксперимент по выбору, выключенный по умолчанию: до 100 процессов, смена групп через 10 секунд после полного запуска группы. Помещающаяся очередь остаётся запущенной. Обычный режим 1–10 игр / 1–1440 минут сохранён.
- Фоновый запуск с отменой и остановка сохраняют отзывчивость интерфейса; частичные группы откатываются, ошибки остановки сохраняются для повтора.
- Полный русский и английский интерфейс. Переводы окон допускают чтение во время атомарной замены текста.

Релиз проверяется 51 существующей проверкой и четырьмя проверками очистки очереди. Поведение 100 процессов моделируется; проверка с настоящими окнами запускает десять helpers. Распознавание Discord и зачёт одновременных игр или коротких сессий не подтверждены.

---

# Discord Game Idler 1.0.0

## English

- Russian and English interface, including status messages, errors, dialogs, and helper windows.
- Live language switching preserves the queue and running session; the choice is saved locally.
- Search a bundled public Windows-game catalog and update it when online.
- Run 1–10 lightweight simulated game processes, rotate larger queues in groups, and stop all owned processes.
- Remove conflicting EXE names while keeping the first queued game.
- Validated cache paths, rollback on partial launch failures, and retryable cleanup.

Windows 10/11 x64. No Python installation is needed for the packaged EXE.
The .NET Framework 4.x compiler must be available on Windows.
**Discord recognition and badge/playtime credit remain unconfirmed.** The timer
shows local elapsed time and does not accelerate or verify server-side progress.

## Русский

- Русский и английский интерфейс: надписи, статусы, ошибки, диалоги и окна имитации.
- Переключение языка без потери очереди и остановки сессии; выбор сохраняется локально.
- Поиск по встроенному публичному каталогу игр Windows и обновление через интернет.
- Одновременный запуск от 1 до 10 лёгких процессов, смена больших очередей группами, остановка всех своих процессов.
- Удаление конфликтующих имён EXE с сохранением первой игры в очереди.
- Проверка путей кэша, откат частичного запуска и повторная остановка после ошибок.

Windows 10/11 x64. Для готового EXE установка Python не нужна.
В Windows должен быть доступен компилятор .NET Framework 4.x.
**Распознавание Discord и зачёт часов/значков не подтверждены.** Таймер показывает
локальное время, не ускоряет и не подтверждает серверный прогресс.
