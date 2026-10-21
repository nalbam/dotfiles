return {
  {
    "sindrets/diffview.nvim",
    cmd = {
      "DiffviewOpen",
      "DiffviewClose",
      "DiffviewToggleFiles",
      "DiffviewFocusFiles",
      "DiffviewRefresh",
      "DiffviewFileHistory",
    },
    keys = {
      { "<leader>gv", "<cmd>DiffviewOpen<cr>", desc = "Git Diff View" },
      { "<leader>gV", "<cmd>DiffviewClose<cr>", desc = "Close Git Diff View" },
    },
    opts = {
      file_panel = {
        win_config = {
          position = "left",
          width = 35,
        },
      },
    },
  },

  -- CLI tools useful for shell / CI / Lua editing.
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      opts.ensure_installed = opts.ensure_installed or {}
      vim.list_extend(opts.ensure_installed, {
        "actionlint",
        "shellcheck",
        "shfmt",
        "stylua",
      })
    end,
  },
}
