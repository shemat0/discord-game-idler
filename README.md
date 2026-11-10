# Discord Game Idler

[Русский](README.ru.md) · English

Discord Game Idler is an experimental Windows tool intended to boost tracked playtime and the number of games played for Discord profile badges, and to help with Discord Quests that require playing a game. It simulates game activity using lightweight Windows processes and Discord's public game catalog.

**Discord detection, badge progress, and Quest completion remain unverified.** The timer measures local session time.

Light and dark themes are available in the same client through **Theme**, next to **Language**. The default is dark; warnings use amber in dark mode and brown in light mode.

## Download and run

From the [latest release](https://github.com/shemat0/discord-game-idler/releases/latest) of [shemat0/discord-game-idler](https://github.com/shemat0/discord-game-idler), download `DiscordGameIdler-<version>-Windows-x64.zip`, extract it, and open `DiscordGameIdler.exe`. Windows 10/11 x64 is supported. Python and the compact native Windows helper are bundled. Stop and close an older version before opening the new one.

1. Open Discord desktop. Discord's [badge documentation](https://support.discord.com/hc/en-us/articles/44369363856663-Discord-Profile-Badges-What-Each-Badge-Means) says these badges require **Use data to personalize my Discord experience**. Check your game activity settings as well.
2. Search for games and click **Add selected**. After bulk selection, click **Remove conflicts** to retain the first game for each EXE basename. Matching ignores folders and letter case; the dialog shows removal totals and up to ten names. **Clear queue** empties the whole queue while idle, without changing the catalog or search; it is disabled during operations, sessions, or unfinished cleanup.
3. Begin with one game and check **Discord → Registered Games**. A helper window opens; it may be minimized. A manually added window or a local timer does not prove verified game or badge credit.
4. Set **At the same time** to 1–10 (default: 10). Fewer selected games produce fewer processes, with no duplicates. A queue that fits stays running. Larger queues rotate in groups: 25 games at a limit of 10 form groups of 10, 10, and 5, then repeat.
5. **Stop** or closing the main app stops its processes. Closing any helper window stops the current group. Launch failures roll back the partial group. Failed stops retain the remaining processes for another Stop attempt. After errors there are no automatic relaunches.

## Independent experimental controls (1.2.0)

Both experiments are **off at startup** and independent. Each checkbox has an adjacent **May reduce system performance** warning.

| Checkbox beside the field | Off | On |
| --- | --- | --- |
| Concurrent game count | 1–10 games | 1–100 games; your count is preserved when enabling |
| Group interval | 1–1440 minutes | 10–86400 seconds, configurable; default 10 seconds |

After enabling the concurrent game experiment, a **Super experiment: up to 1000** checkbox appears below it. It starts unchecked and raises the cap to 1000 without changing the interval. **It may work incorrectly with your system and use more than 1 GB of RAM.** Turning it off clamps the count to 100. Turning the concurrent game experiment off clears the super experiment and clamps the count to 10.

Examples: enable only the count experiment for **100 games held for 180 minutes**; enable only the time experiment for **one game at a time, changing every 10 seconds** through a multi-game queue; enable both for **100 games per group, changing every 10 seconds**. If the whole selected queue fits the chosen count, it stays running instead of restarting. One selected game therefore stays running until Stop.

Switching time units preserves the separate minutes and seconds inputs, including an hours-long minute value. Toggling either checkbox does not change the other checkbox or its input. Turning the count experiment off clamps a count above 10 back to 10. Both controls are locked during operations, sessions, and unfinished cleanup.

A group's configured dwell interval starts **after every process in the group has launched**. Larger queues rotate without overlapping groups; a remainder group is not dropped. Starting, rotation, and cleanup run in the background. **Stop** cancels between process launches and waits for the current system operation before cleaning up. Language switching remains available between operations.

The automated checks simulate 100 processes and retain the ten-real-process smoke test; they do not open 100 windows. **Discord recognition and credit for short sessions or concurrent games are unconfirmed.** These controls change local processes, not Discord's server-side counters.

## Languages and local data

Choose **Язык / Language → Русский or English**. The interface, existing status/error messages, and running helper windows change without restarting the session. Game titles stay as supplied by the catalog. The initial language follows Windows UI language (Russian → RU, otherwise EN); your choice is saved in `%LOCALAPPDATA%\DiscordGameIdler\settings.json`.

Switch **Theme → Dark / Light** live without resetting the queue, session, or timers. Running helper windows follow the choice without restarting. Language and theme are saved together in `settings.json`, and changing one preserves the other. Appearance selectors are briefly locked while a background operation is busy.

The cache, downloaded catalog, generated helper files, and helper translation file are stored in `%LOCALAPPDATA%\DiscordGameIdler`. Packaged Windows environments may redirect that directory to their local cache. The app uses no Discord account token, login, self-bot, or Discord client modification. It does not auto-start a session.

The bundled catalog is a reduced public snapshot dated **2026-11-04** with 10,445 usable Windows games. **Update catalog** downloads fresh metadata; the bundled or previously cached copy remains available if the download fails. See [third-party information](THIRD_PARTY_NOTICES.md) for the source and attribution.

## Run from source

Use 64-bit Windows and Python 3.14 with Tkinter. Source runs use the built native helper when available, with the Windows .NET Framework 4.x compiler as a fallback.

```powershell
python app.py
```

`launch.cmd` is also available. To run the behavior and localization checks:

```powershell
python -m unittest discover -v -p "test_*.py"
python -m py_compile app.py core.py i18n.py theme.py version.py build.py
```

Windows integration tests briefly open their own helper windows and close them. They check process/window lifecycle, ten-process cleanup, rotation boundaries, rollback, conflict filtering, translations, saved preferences, and live language switching. They do not verify Discord badge credit.

## Build a release

Build with Python 3.14 x64, the packages in `requirements-build.txt`, and Visual Studio Build Tools with the x64 C++ toolset and Windows SDK.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe build.py
```

The build runs checks and writes `DiscordGameIdler.exe`, the bilingual ZIP, and `SHA256SUMS.txt` under `dist/v1.3.0/`. No GitHub credentials are needed to build. This project is independent of Discord.
