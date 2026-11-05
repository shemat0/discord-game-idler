# Discord Game Idler

[Русский](README.ru.md) · English

Experimental Windows desktop utility for simulating game processes from Discord's public detectable-application catalog. It runs lightweight helper windows; it does not install or launch the actual games.

**Discord recognition and badge/playtime credit are not guaranteed or verified by this app.** Running ten processes does not establish that Discord counts ten games or multiplies playtime. The timer measures only local elapsed time.

## Download and run

From the [latest release](https://github.com/shemat0/discord-game-idler/releases/latest) of [shemat0/discord-game-idler](https://github.com/shemat0/discord-game-idler), download `DiscordGameIdler-<version>-Windows-x64.zip`, extract it, and open `DiscordGameIdler.exe`. Windows 10/11 x64 is supported. Python is bundled; the .NET Framework 4.x compiler must already be available on Windows. Stop and close an older version before opening the new one.

1. Open Discord desktop. Discord's [badge documentation](https://support.discord.com/hc/en-us/articles/44369363856663-Discord-Profile-Badges-What-Each-Badge-Means) says these badges require **Use data to personalize my Discord experience**. Check your game activity settings as well.
2. Search for games and click **Add selected**. After bulk selection, click **Remove conflicts** to retain the first game for each EXE basename. Matching ignores folders and letter case; the dialog shows removal totals and up to ten names. **Clear queue** empties the whole queue while idle, without changing the catalog or search; it is disabled during operations, sessions, or unfinished cleanup.
3. Begin with one game and check **Discord → Registered Games**. A helper window opens; it may be minimized. A manually added window or a local timer does not prove verified game or badge credit.
4. Set **At the same time** to 1–10 (default: 10). Fewer selected games produce fewer processes, with no duplicates. A queue that fits stays running. Larger queues rotate in groups: 25 games at a limit of 10 form groups of 10, 10, and 5, then repeat.
5. **Stop** or closing the main app stops its processes. Closing any helper window stops the current group. Launch failures roll back the partial group. Failed stops retain the remaining processes for another Stop attempt. After errors there are no automatic relaunches.

## Opt-in experimental mode (1.1.1)

Version **1.1.1** adds experimental group rotation alongside the normal mode.

**Experimental: up to 100 games** is off at startup. Enable it while idle to set the maximum/default concurrency to 100. The normal 1–10 game limit and 1–1440 minute interval remain unchanged when it is off. Disabling experimental mode restores 10 games and 15 minutes. The mode cannot change during a session, an operation, or unfinished cleanup.

In experimental mode, a fully launched group stays running for **at least 10 seconds** before the next group replaces it. Startup time is excluded from that dwell interval. A queue of 205 games at a limit of 100 produces groups of 100, 100, and 5; a queue that fits stays running instead of repeatedly restarting. Groups never overlap. Duplicate EXE-name conflicts must still be removed.

Starting, rotation, and cleanup run in the background. **Stop** cancels between process launches and cleans up the partial group; it waits for any current system operation. Language switching is briefly unavailable while an operation is busy, and remains available between operations. Up to 100 real helper windows may use substantial resources. The automated checks simulate 100 processes and retain the ten-real-process smoke test; they do not open 100 windows.

**Discord recognition and credit for ten-second sessions or concurrent games are unconfirmed.** This mode changes local processes, not Discord's server-side counters.

## Languages and local data

Choose **Язык / Language → Русский or English**. The interface, existing status/error messages, and running helper windows change without restarting the session. Game titles stay as supplied by the catalog. The initial language follows Windows UI language (Russian → RU, otherwise EN); your choice is saved in `%LOCALAPPDATA%\DiscordGameIdler\settings.json`.

The cache, downloaded catalog, generated helper files, and helper translation file are stored in `%LOCALAPPDATA%\DiscordGameIdler`. Packaged Windows environments may redirect that directory to their local cache. The app uses no Discord account token, login, self-bot, or Discord client modification. It does not auto-start a session.

The bundled catalog is a reduced public snapshot dated **2026-11-04** with 10,445 usable Windows games. **Update catalog** downloads fresh metadata; the bundled or previously cached copy remains available if the download fails. See [third-party information](THIRD_PARTY_NOTICES.md) for the source and attribution.

## Run from source

Use 64-bit Windows and Python 3.14 with Tkinter. Runtime code uses the Python standard library.

```powershell
python app.py
```

`launch.cmd` is also available. To run the behavior and localization checks:

```powershell
python -m unittest discover -v -p "test_*.py"
python -m py_compile app.py core.py i18n.py version.py build.py
```

Windows integration tests briefly open their own helper windows and close them. They check process/window lifecycle, ten-process cleanup, rotation boundaries, rollback, conflict filtering, translations, saved preferences, and live language switching. They do not verify Discord badge credit.

## Build a release

The tested toolchain is Python 3.14.7 x64 and the versions in `requirements-build.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe build.py
```

The build runs checks and writes `DiscordGameIdler.exe`, the bilingual ZIP, and `SHA256SUMS.txt` under `dist/v1.1.1/`. No GitHub credentials are needed to build. This project is independent of Discord.
