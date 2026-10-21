# Neovim / LazyVim configuration

This configuration adds language tooling and local key mappings to LazyVim. It is an add-on: enable it with `dot add nvim`.

## Prerequisites

Install the tools with Homebrew:

```bash
brew install neovim git ripgrep fd fzf lazygit tree-sitter-cli
```

On Linux, install the same tools with Homebrew or the distribution's packages. The configuration uses the system clipboard (`unnamedplus`), which needs `xclip` or `xsel` on X11, `wl-clipboard` on Wayland, or `win32yank` on WSL.

Use a Nerd Font for icons. A C compiler and curl are also required; on macOS, complete Xcode Command Line Tools installation before starting Neovim. The parser CLI comes from [tree-sitter-cli](https://formulae.brew.sh/formula/tree-sitter-cli).

The first launch needs network access to download the plugin manager and plugins. Check the [current LazyVim requirements](https://www.lazyvim.org/) before installing; this repository does not pin a LazyVim release.

## Install

```bash
dot add nvim
nvim
```

The `nvim` module copies `config/nvim/nvim/` to `~/.config/nvim` and keeps it current on each `dot up`. It installs the configuration when `~/.config/nvim` is missing or when the repository version changed since the last install; local edits and Neovim's own `lazy-lock.json` stay until then. Before it replaces a configuration, it moves the existing one, including a symlink, to `~/.config/nvim.bak-<timestamp>` and prints the backup path; if that path exists, it appends `.1`. Use `dot remove nvim` to manage the configuration yourself. Neovim's plugin, cache and state directories are not backed up.

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
