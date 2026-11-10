# Discord Game Idler 1.3.2

## English

- The super experiment confirmation dialog opens centered over the main window.

## Русский

- Окно подтверждения суперэксперимента открывается по центру главного окна.

---

# Discord Game Idler 1.3.1

## English

- Turning on either experimental mode shows a warning about increased system load.
- The mode for up to 1000 games requires selecting **I understand the risks** before clicking **Enable**. The dialog warns about possible system instability and memory use above 1 GB.

## Русский

- При включении любого экспериментального режима появляется предупреждение о повышенной нагрузке на компьютер.
- Для запуска режима до 1000 игр нужно отметить **«Я осознаю риски»** и нажать **«Включить»**. Окно предупреждает о возможной нестабильной работе системы и потреблении более 1 ГБ ОЗУ.

---

# Discord Game Idler 1.3.0

## English

- Packaged helpers use compact native Win32 windows with a 310 × 105 pixel client area and lower memory use.
- Enable the concurrent game experiment to reveal a separate super experiment. It raises the cap to 1000 and keeps the timing mode and interval independent.
- The checkbox warns that the mode may work incorrectly with your system and use more than 1 GB of RAM.

High counts are tested with simulated processes. Discord credit remains unconfirmed.

## Русский

- В сборку входят компактные нативные окна Win32 с клиентской областью 310 × 105 пикселей и меньшим расходом памяти.
- В эксперименте количества доступна отдельная галочка суперэксперимента. Она поднимает лимит до 1000 и сохраняет настройки интервала.
- Возле галочки есть предупреждение о возможной некорректной работе с системой и потреблении больше 1 ГБ ОЗУ.

Большие группы проверяются на модели процессов. Зачёт активности Discord не подтверждён.

---

# Discord Game Idler 1.2.1

## English

- Show the total number of queued games in the queue heading.
- Update the count after adding, removing, clearing or filtering conflicting games; keep it translated when switching languages.
- Preserve the unified light/dark theme client and independent experimental controls.

## Русский

- Добавлен счётчик общего количества игр в заголовке очереди.
- Счётчик обновляется при добавлении, удалении, очистке и фильтрации конфликтов; переводится при смене языка.
- Сохранены единый клиент со светлой/тёмной темами и независимые экспериментальные настройки.

---

# Discord Game Idler 1.2.0

## English

- A single client with live light/dark theme selection next to language; both preferences are saved together. Running helper windows change theme without restarting.
- Split the experiment into two independent checkboxes beside their respective fields: concurrency up to 100 and configurable interval in seconds (10–86400).
- Normal defaults remain 1–10 games and 1–1440 minutes; both experiments are off at startup.
- Support 100 games for hours, one game at a time every 10 seconds, or 100 games every 10 seconds. A fitting queue stays running.
- Preserve the other experiment's state and input when toggling. Minutes and seconds retain their own values.
- Show **May reduce system performance** beside both experimental controls.
- Preserve RU/EN, background cancellation, full-group dwell timing, rollback, conflict filtering, and queue clearing.

Validation: 69 tests passed, including live theme switching, shared language/theme preferences, and process cleanup. 100-process checks use a simulated backend; the real smoke test remains ten windows. Discord credit remains unconfirmed.

## Русский

- Один клиент с живым переключением светлой/тёмной темы рядом с языком; обе настройки сохраняются вместе. Окна имитации меняют тему без перезапуска.
- Эксперимент разделён на две независимые галочки возле соответствующих полей: до 100 игр и настраиваемые секунды (10–86400).
- Обычные пределы остаются прежними: 1–10 игр и 1–1440 минут; при старте обе галочки выключены.
- Поддерживаются 100 игр на часы, одна игра за раз каждые 10 секунд и 100 игр каждые 10 секунд. Помещающаяся очередь остаётся запущенной.
- Переключение сохраняет состояние и ввод другого эксперимента. Минуты и секунды хранят отдельные значения.
- Возле обеих галочек показано **«Может снизить производительность системы»**.
- Сохранены RU/EN, фоновая отмена, отсчёт после полного запуска группы, откат, фильтрация конфликтов и очистка очереди.

Проверка: 69 тестов прошли, включая смену темы без перезапуска, совместное сохранение языка/темы и остановку процессов. Проверки 100 процессов выполняются на модели; настоящая проверка по-прежнему открывает десять окон. Зачёт Discord не подтверждён.

---

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
