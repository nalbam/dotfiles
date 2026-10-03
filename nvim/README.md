# Neovim / LazyVim configuration for macOS

This configuration adds language tooling and local key mappings to LazyVim. Install it separately; `run.sh` does not run `nvim/install.sh`.

## Prerequisites

Install the tools with Homebrew:

```bash
brew install neovim git ripgrep fd fzf lazygit tree-sitter-cli
```

Use a Nerd Font for icons. A C compiler and curl are also required; on macOS, complete Xcode Command Line Tools installation before starting Neovim. The parser CLI comes from [tree-sitter-cli](https://formulae.brew.sh/formula/tree-sitter-cli).

The first launch needs network access to download the plugin manager and plugins. Check the [current LazyVim requirements](https://www.lazyvim.org/) before installing; this repository does not pin a LazyVim release.

## Install

From the repository root:

```bash
bash nvim/install.sh
nvim
```

The installer copies `nvim/nvim/` to `~/.config/nvim`. It moves an existing configuration to `~/.config/nvim.bak-<timestamp>` and prints the backup path. It does not back up Neovim's separate plugin, cache, or state directories.

Wait for plugin installation to finish. Open `:Lazy` to inspect plugin status, `:Mason` to inspect external tools, and `:LazyHealth` to load plugins and check their health, as described in the [LazyVim installation guide](https://www.lazyvim.org/installation). If installation fails, use the reported error to check network access or the missing tool before retrying.

To restore a saved configuration, close Neovim, move the new configuration aside, and move the printed backup path back to `~/.config/nvim`.

## Included tooling

[`lazy.lua`](nvim/lua/config/lazy.lua) enables extras for JSON, YAML, Markdown, Docker, Terraform, Helm, Go, Python, TypeScript, and Prettier.

[`options.lua`](nvim/lua/config/options.lua) selects Pyright and Ruff for Python and vtsls for TypeScript. [`tools.lua`](nvim/lua/plugins/tools.lua) adds Diffview and configures Mason to install actionlint, shellcheck, shfmt, and stylua.

## Local key mappings

LazyVim's leader key is `Space`. These mappings are defined in this repository's [keymaps](nvim/lua/config/keymaps.lua) and [tools](nvim/lua/plugins/tools.lua).

| Key | Action |
|-----|--------|
| `Space w` | Save the current file |
| `Space q` | Quit the current window |
| `Space Q` | Quit all windows |
| `Space gv` | Open Git Diffview with the file panel on the left |
| `Space gV` | Close Git Diffview |
| `jk` in insert mode | Return to normal mode |
| `Esc` in normal mode | Clear search highlighting |
| `<` / `>` in visual mode | Indent and keep the selection |

Other mappings come from the installed LazyVim version. Use `:map` to inspect the mappings in the running editor.
