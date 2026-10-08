@echo off
rem Windows-Build von ConnectFour Studio (Qt) mit PyInstaller.
rem Aufruf im Projektordner:  packaging\windows\build_windows.bat
rem Voraussetzung: 64-bit Python 3.10-3.14 (py-Launcher).
setlocal
cd /d "%~dp0\..\.."

if not exist build\winvenv (
    py -m venv build\winvenv || goto :error
)
build\winvenv\Scripts\python -m pip install --upgrade pip || goto :error
build\winvenv\Scripts\pip install -r requirements.txt pyinstaller || goto :error
build\winvenv\Scripts\python packaging\windows\prepare_build.py || goto :error
build\winvenv\Scripts\pyinstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller packaging\windows\connectfour_studio_qt.spec || goto :error

echo.
echo Fertig: dist\ConnectFour Studio Qt\ConnectFour Studio Qt.exe
exit /b 0

:error
echo Build fehlgeschlagen.
exit /b 1
