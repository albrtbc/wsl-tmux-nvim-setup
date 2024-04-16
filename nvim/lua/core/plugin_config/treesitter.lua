require 'nvim-treesitter.configs'.setup {
  -- A list of parser names, or "all"
  ensure_installed = { "c_sharp", "lua", "vim", "vimdoc", "query", "json", "yaml", "xml", "sql", "python" },

  -- Install parsers synchronously
  sync_install = false,
  auto_install = true,
  highlight = {
    enable = true,
  },
}
