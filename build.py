"""Validate and package a Windows release. Run from any working directory."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from version import __version__

ROOT = Path(__file__).resolve().parent


def run(*arguments):
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def main():
    if os.name != "nt" or sys.maxsize <= 2**32:
        raise SystemExit("Build on 64-bit Windows with 64-bit Python.")
    run("-m", "unittest", "discover", "-v", "-p", "test_*.py")
    run("-m", "py_compile", "app.py", "core.py", "i18n.py", "theme.py", "version.py", "build.py")
    output = ROOT / "dist" / ("v" + __version__)
    work = ROOT / "build" / ("v" + __version__)
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    run("-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "DiscordGameIdler", "--add-data", str(ROOT / "catalog.json") + ";.",
        "--add-data", str(ROOT / "licenses") + ";licenses",
        "--distpath", str(output), "--workpath", str(work / "work"), "--specpath", str(work),
        str(ROOT / "app.py"))
    executable = output / "DiscordGameIdler.exe"
    archive = output / f"DiscordGameIdler-{__version__}-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        bundle.write(executable, executable.name)
        for name in ("README.md", "README.ru.md", "THIRD_PARTY_NOTICES.md", "RELEASE_NOTES.md"):
            bundle.write(ROOT / name, name)
        for path in sorted((ROOT / "licenses").glob("*")):
            if path.is_file():
                bundle.write(path, "licenses/" + path.name)
    checksums = []
    for path in (executable, archive):
        checksums.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name)
    (output / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print("Release files: " + str(output))


if __name__ == "__main__":
    main()
