#!/usr/bin/env bash
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/nvim"
DST="$HOME/.config/nvim"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$HOME/.config"

if [[ -e "$DST" ]]; then
  BACKUP="$HOME/.config/nvim.bak-$STAMP"
  echo "Backing up existing config: $DST -> $BACKUP"
  mv "$DST" "$BACKUP"
fi

cp -R "$SRC" "$DST"

echo "Installed Neovim config to: $DST"
echo "Now run: nvim"
