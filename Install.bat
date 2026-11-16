@echo off
rem campaign-kit - self-contained installer (Windows 10+): uv + managed Python + wizard.
setlocal
cd /d "%~dp0"
if not exist ".tools" mkdir ".tools"

if not exist ".tools\uv.exe" (
  echo downloading uv...
  if "%PROCESSOR_ARCHITECTURE%"=="ARM64" (
    curl -fsSL -o ".tools\uv.zip" "https://github.com/astral-sh/uv/releases/latest/download/uv-aarch64-pc-windows-msvc.zip"
  ) else (
    curl -fsSL -o ".tools\uv.zip" "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"
  )
  tar -xf ".tools\uv.zip" -C ".tools"
  del ".tools\uv.zip"
)

if not exist ".venv\Scripts\python.exe" (
  echo preparing managed Python 3.12 (no admin)...
  ".tools\uv.exe" venv --python 3.12 ".venv"
)
echo installing dependencies...
".tools\uv.exe" pip install --python ".venv\Scripts\python.exe" -r requirements.txt

set "INBOX=%~1"
set "COPY="
if "%~2"=="--copy" set "COPY=1"
if "%~1"=="--copy" (
  set "COPY=1"
  set "INBOX=%~2"
)
if "%INBOX%"=="" set /p INBOX="campaign folder (Enter = Desktop\my-campaign): "
if "%INBOX%"=="" set "INBOX=%USERPROFILE%\Desktop\my-campaign"
if defined COPY (
  echo opening the copy wizard...
  ".venv\Scripts\python.exe" -m kit.cli copy onboard "%INBOX%"
) else (
  echo opening the onboarding wizard...
  ".venv\Scripts\python.exe" -m kit.cli onboard "%INBOX%"
)
pause