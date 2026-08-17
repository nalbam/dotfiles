# Neovim / LazyVim config for macOS

## Prerequisites

```bash
brew install neovim git ripgrep fd fzf lazygit tree-sitter
```

A Nerd Font is recommended for icons.

## Install

```bash
./install.sh
nvim
```

The installer backs up an existing `~/.config/nvim` as `~/.config/nvim.bak-<timestamp>`.

## Included LazyVim extras

- JSON
- YAML
- Markdown
- Docker
- Terraform
- Helm
- Go
- Python (Pyright + Ruff)
- TypeScript (vtsls)
- Prettier

Additional tools installed through Mason:

- actionlint
- shellcheck
- shfmt
- stylua

## Useful keys

LazyVim leader key is `Space`.

- `Space Space` — find files
- `Space /` — grep project
- `Space e` — explorer
- `Space gg` — Lazygit
- `Space w` — save
- `Space q` — quit
- `gd` — go to definition
- `gr` — references
- `K` — hover docs
- `Space ca` — code action
- `Space cr` — rename
- `jk` — escape insert mode

## Useful commands

```vim
:Lazy
:Mason
:LazyExtras
:checkhealth
```
