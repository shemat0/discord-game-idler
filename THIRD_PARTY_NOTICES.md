# Third-party information / Сторонние материалы

`catalog.json` contains a reduced snapshot of public Discord application metadata,
downloaded on **2026-11-04** from
<https://discord.com/api/v9/applications/detectable>.
Only application IDs, names, and Windows executable descriptors are retained.
The app filters this into 10,445 usable Windows entries. These entries are
descriptive metadata, not bundled games or Discord client code.

Discord and game names are trademarks of their respective owners. This project
is independent and is not affiliated with, endorsed by, or supported by Discord.

The packaged Windows executable includes Python and Tcl/Tk through PyInstaller.
Those projects retain their respective licenses; see
[Python](https://docs.python.org/3/license.html),
[Tcl/Tk](https://www.tcl-lang.org/software/tcltk/license.html), and
[PyInstaller](https://pyinstaller.org/en/stable/license.html).
Verbatim notices copied from the installed distributions are included in
[`licenses/`](licenses/): Python's complete `LICENSE.txt`, Tcl/Tk 9.0.4's
`license.terms` files, and PyInstaller 6.22.3's `COPYING.txt` (including its
bootloader exception). These notices are included in the ZIP and embedded EXE.
The small runtime helper is generated from this repository's `core.py`, using
the .NET Framework compiler already installed on Windows.

---

`catalog.json` — сокращённый снимок публичных метаданных приложений Discord
от **4 ноября 2026 года**. Сохранены только ID, названия и описания исполняемых
файлов Windows. Это данные каталога, а не сами игры и не код клиента Discord.
Проект независимый, не связан с Discord и не поддерживается Discord.
Названия Discord и игр принадлежат соответствующим правообладателям.
В готовом EXE используются Python и Tcl/Tk, упакованные PyInstaller;
их собственные лицензии сохраняются по ссылкам выше.
