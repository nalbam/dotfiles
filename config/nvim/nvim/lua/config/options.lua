-- Loaded before lazy.nvim starts.
local opt = vim.opt

-- macOS clipboard
opt.clipboard = "unnamedplus"

-- Editor behavior
opt.number = true
opt.relativenumber = true
opt.cursorline = true
opt.wrap = false
opt.scrolloff = 8
opt.sidescrolloff = 8
opt.mouse = "a"

-- Indentation defaults; language formatters may override these.
opt.tabstop = 2
opt.shiftwidth = 2
opt.softtabstop = 2
opt.expandtab = true
opt.smartindent = true

-- Search
opt.ignorecase = true
opt.smartcase = true

-- Files / responsiveness
opt.undofile = true
opt.updatetime = 250
opt.timeoutlen = 300

-- UI
opt.termguicolors = true
opt.signcolumn = "yes"

-- LazyVim language-extra choices
vim.g.lazyvim_python_lsp = "pyright"
vim.g.lazyvim_python_ruff = "ruff"
vim.g.lazyvim_ts_lsp = "vtsls"
