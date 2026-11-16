#!/bin/sh
# campaign-kit — self-contained installer: uv + managed Python + deps + wizard.
# No pre-installed Python or admin needed: uv downloads its own CPython into this
# folder. Usage: ./install.sh [campaign-folder] [--no-open]
set -eu
cd "$(dirname "$0")"
KIT=$(pwd)
mkdir -p .tools

if [ ! -x .tools/uv ]; then
  OS=$(uname -s); ARCH=$(uname -m)
  case "$OS/$ARCH" in
    Darwin/arm64)  TARGET=aarch64-apple-darwin ;;
    Darwin/x86_64) TARGET=x86_64-apple-darwin ;;
    Linux/aarch64|Linux/arm64) TARGET=aarch64-unknown-linux-gnu ;;
    Linux/x86_64)  TARGET=x86_64-unknown-linux-gnu ;;
    *) echo "unsupported system: $OS/$ARCH"; exit 1 ;;
  esac
  echo "downloading uv ($TARGET)…"
  curl -fsSL "https://github.com/astral-sh/uv/releases/latest/download/uv-$TARGET.tar.gz" -o .tools/uv.tar.gz
  tar -xzf .tools/uv.tar.gz -C .tools --strip-components=1 "uv-$TARGET/uv"
  rm .tools/uv.tar.gz
fi

if [ ! -x .venv/bin/python ]; then
  echo "preparing managed Python 3.12 (no admin)…"
  .tools/uv venv --python 3.12 .venv
fi
echo "installing dependencies…"
.tools/uv pip install --python .venv/bin/python -r requirements.txt

INBOX=""
COPY=0
FLAGS=""
for a in "$@"; do
  case "$a" in
    --copy) COPY=1 ;;
    --*) FLAGS="$FLAGS $a" ;;
    *) [ -z "$INBOX" ] && INBOX="$a" ;;
  esac
done
if [ -z "$INBOX" ]; then
  printf "campaign folder (Enter = ~/Desktop/my-campaign): "
  read -r INBOX || true
  INBOX=${INBOX:-$HOME/Desktop/my-campaign}
fi
if [ "$COPY" = "1" ]; then
  echo "opening the copy wizard…"
  exec .venv/bin/python -m kit.cli copy onboard "$INBOX" $FLAGS
fi
echo "opening the onboarding wizard…"
exec .venv/bin/python -m kit.cli onboard "$INBOX" $FLAGS