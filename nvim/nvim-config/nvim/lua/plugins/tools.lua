return {
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
