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


def build_native_helper():
    x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    vswhere = x86 / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not vswhere.is_file():
        raise SystemExit("Install Visual Studio Build Tools with the x64 C++ toolset and Windows SDK.")
    installation = subprocess.check_output(
        [str(vswhere), "-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
         "-property", "installationPath"], text=True).strip()
    if not installation:
        raise SystemExit("Visual Studio's x64 C++ toolset was not found.")
    msvc = max((Path(installation) / "VC" / "Tools" / "MSVC").iterdir(), key=lambda path: tuple(map(int, path.name.split("."))))
    sdk = x86 / "Windows Kits" / "10"
    sdk_version = max((path.name for path in (sdk / "Include").iterdir()
                       if (sdk / "Lib" / path.name / "um" / "x64" / "user32.lib").is_file()),
                      key=lambda value: tuple(map(int, value.split("."))))
    output = ROOT / "build" / "native"
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["INCLUDE"] = ";".join(map(str, [msvc / "include", *(sdk / "Include" / sdk_version / part for part in ("ucrt", "shared", "um"))]))
    env["LIB"] = ";".join(map(str, [msvc / "lib" / "x64", *(sdk / "Lib" / sdk_version / part / "x64" for part in ("ucrt", "um"))]))
    compiler = msvc / "bin" / "Hostx64" / "x64" / "cl.exe"
    subprocess.run([str(compiler), "/nologo", "/O1", "/MT", "/utf-8", "/DUNICODE", str(ROOT / "helper.c"),
                    "/Fe:helper-native.exe", "user32.lib", "gdi32.lib", "shell32.lib",
                    "/link", "/SUBSYSTEM:WINDOWS"], cwd=output, env=env, check=True)
    return output / "helper-native.exe"


def main():
    if os.name != "nt" or sys.maxsize <= 2**32:
        raise SystemExit("Build on 64-bit Windows with 64-bit Python.")
    native_helper = build_native_helper()
    run("-m", "unittest", "discover", "-v", "-p", "test_*.py")
    run("-m", "py_compile", "app.py", "core.py", "i18n.py", "theme.py", "version.py", "build.py")
    output = ROOT / "dist" / ("v" + __version__)
    work = ROOT / "build" / ("v" + __version__)
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    run("-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "DiscordGameIdler", "--add-data", str(ROOT / "catalog.json") + ";.",
        "--add-data", str(ROOT / "licenses") + ";licenses",
        "--add-data", str(native_helper) + ";.",
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
