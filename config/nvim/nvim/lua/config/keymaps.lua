-- Loaded on the VeryLazy event.
local map = vim.keymap.set

map("n", "<leader>w", "<cmd>w<cr>", { desc = "Save file" })
map("n", "<leader>q", "<cmd>q<cr>", { desc = "Quit window" })
map("n", "<leader>Q", "<cmd>qa<cr>", { desc = "Quit all" })

-- Fast insert-mode escape.
map("i", "jk", "<Esc>", { desc = "Exit insert mode" })

-- Clear search highlighting.
map("n", "<Esc>", "<cmd>nohlsearch<cr>", { desc = "Clear search highlight" })

-- Keep selection after indenting.
map("v", "<", "<gv")
map("v", ">", ">gv")
