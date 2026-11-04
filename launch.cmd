@echo off
chcp 65001 >nul
cd /d "%~dp0"
pythonw app.py
if errorlevel 1 (
  echo Install Python 3 with Tkinter, or use the standalone exe.
  echo Установите Python 3 с Tkinter или используйте готовый EXE.
  pause
)
