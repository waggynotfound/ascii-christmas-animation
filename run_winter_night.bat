@echo off
setlocal
title Winter Night
cd /d "%~dp0"

rem Big window, dark background, so the scene has room and contrast.
mode con: cols=170 lines=46
color 0F

rem Find a real Python 3 (python, then the py launcher).
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
    where py >nul 2>nul && set "PY=py"
)

if not defined PY (
    echo.
    echo   Python 3 was not found.
    echo   Install it from https://www.python.org/downloads/
    echo   During setup tick "Add python.exe to PATH", then run this file again.
    echo.
    pause
    exit /b 1
)

rem Run the scene. Ctrl+C stops it; the window closes when it exits.
%PY% "winter_night_ascii.py"

echo.
echo   Thanks for watching. Press any key to close.
pause >nul
endlocal
