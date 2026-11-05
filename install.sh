#!/bin/sh
# campaign-kit — instalador autocontido: uv + Python gerenciado + deps + wizard.
# Não precisa de Python pré-instalado nem de admin: o uv baixa um CPython próprio
# para dentro desta pasta. Uso: ./install.sh [pasta-da-campanha] [--no-open]
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
    *) echo "sistema não suportado: $OS/$ARCH"; exit 1 ;;
  esac
  echo "baixando uv ($TARGET)…"
  curl -fsSL "https://github.com/astral-sh/uv/releases/latest/download/uv-$TARGET.tar.gz" -o .tools/uv.tar.gz
  tar -xzf .tools/uv.tar.gz -C .tools --strip-components=1 "uv-$TARGET/uv"
  rm .tools/uv.tar.gz
fi

if [ ! -x .venv/bin/python ]; then
  echo "preparando Python 3.12 gerenciado (sem admin)…"
  .tools/uv venv --python 3.12 .venv
fi
echo "instalando dependências…"
.tools/uv pip install --python .venv/bin/python -r requirements.txt

INBOX=""
if [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; then INBOX=$1; shift; fi
if [ -z "$INBOX" ]; then
  printf "pasta da campanha (Enter = ~/Desktop/minha-campanha): "
  read -r INBOX || true
  INBOX=${INBOX:-$HOME/Desktop/minha-campanha}
fi
echo "abrindo o wizard de onboarding…"
exec .venv/bin/python -m kit.cli onboard "$INBOX" "$@"