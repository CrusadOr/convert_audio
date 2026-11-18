@echo off
setlocal
cd /d "%~dp0"

echo Building audio_convert.exe from audio_convert.py...

if not exist "audio_convert.py" (
    echo ERROR: audio_convert.py must be next to build_exe.bat.
    goto :failed
)

py -3 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 or the Windows py launcher was not found.
    goto :failed
)

echo Checking PyInstaller (minimum secure version: 6.22.1)...
py -3 -m pip install "pyinstaller>=6.22.1"
if errorlevel 1 goto :failed

py -3 -m PyInstaller --noconfirm --clean --onefile --console --name audio_convert "audio_convert.py"
if errorlevel 1 goto :failed

if not exist "dist\audio_convert.exe" (
    echo ERROR: The build finished without producing the expected EXE.
    goto :failed
)

echo.
echo SUCCESS: "%~dp0dist\audio_convert.exe"
echo Put ffmpeg.exe and ffprobe.exe next to the EXE, or add them to PATH.
echo Run the EXE from PowerShell with a mode and a file or folder path.
pause
exit /b 0

:failed
echo.
echo Build failed. Check the message above.
pause
exit /b 1
