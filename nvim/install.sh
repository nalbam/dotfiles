#!/usr/bin/env bash
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/nvim"
DST="$HOME/.config/nvim"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$HOME/.config"

if [[ -e "$DST" || -L "$DST" ]]; then
  BACKUP="$HOME/.config/nvim.bak-$STAMP"
  SUFFIX=0
  while [[ -e "$BACKUP" || -L "$BACKUP" ]]; do
    SUFFIX=$((SUFFIX + 1))
    BACKUP="$HOME/.config/nvim.bak-$STAMP-$SUFFIX"
  done
  echo "Backing up existing config: $DST -> $BACKUP"
  mv "$DST" "$BACKUP"
fi

cp -R "$SRC" "$DST"

echo "Installed Neovim config to: $DST"
echo "Now run: nvim"
