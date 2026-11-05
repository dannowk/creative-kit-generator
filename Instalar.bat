@echo off
rem campaign-kit - instalador autocontido (Windows 10+): uv + Python gerenciado + wizard.
setlocal
cd /d "%~dp0"
if not exist ".tools" mkdir ".tools"

if not exist ".tools\uv.exe" (
  echo baixando uv...
  if "%PROCESSOR_ARCHITECTURE%"=="ARM64" (
    curl -fsSL -o ".tools\uv.zip" "https://github.com/astral-sh/uv/releases/latest/download/uv-aarch64-pc-windows-msvc.zip"
  ) else (
    curl -fsSL -o ".tools\uv.zip" "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"
  )
  tar -xf ".tools\uv.zip" -C ".tools"
  del ".tools\uv.zip"
)

if not exist ".venv\Scripts\python.exe" (
  echo preparando Python 3.12 gerenciado (sem admin)...
  ".tools\uv.exe" venv --python 3.12 ".venv"
)
echo instalando dependencias...
".tools\uv.exe" pip install --python ".venv\Scripts\python.exe" -r requirements.txt

set "INBOX=%~1"
if "%INBOX%"=="" set /p INBOX="pasta da campanha (Enter = Desktop\minha-campanha): "
if "%INBOX%"=="" set "INBOX=%USERPROFILE%\Desktop\minha-campanha"
echo abrindo o wizard de onboarding...
".venv\Scripts\python.exe" -m kit.cli onboard "%INBOX%"
pause