-- Project-local Neovim config. Requires `vim.o.exrc = true` (Neovim 0.9+); run `:trust` once.
-- Debugging needs nvim-dap and nvim-dap-python (adapter name "python").
local ok, dap = pcall(require, "dap")
if not ok then
  return
end

local root = vim.fn.getcwd()
local python = root .. "/.venv/bin/python"
local env_file = root .. "/.env"

dap.configurations.python = dap.configurations.python or {}

table.insert(dap.configurations.python, {
  type = "python",
  request = "launch",
  name = "json-config-qt",
  module = "json_config_qt.main",
  pythonPath = python,
  envFile = env_file,
  cwd = root,
  console = "internalConsole",
  justMyCode = true,
})

table.insert(dap.configurations.python, {
  type = "python",
  request = "launch",
  name = "Pytest",
  module = "pytest",
  args = { "tests" },
  pythonPath = python,
  envFile = env_file,
  cwd = root,
  console = "internalConsole",
  justMyCode = false,
})

-- nvim-dap picks configurations by buffer filetype; reuse the python ones everywhere
-- so the app can be launched from any buffer (qml, ini, toml, ...).
vim.api.nvim_create_autocmd("FileType", {
  callback = function(args)
    if args.match ~= "python" then
      dap.configurations[args.match] = dap.configurations.python
    end
  end,
})
for _, buf in ipairs(vim.api.nvim_list_bufs()) do
  local ft = vim.bo[buf].filetype
  if ft ~= "" and ft ~= "python" then
    dap.configurations[ft] = dap.configurations.python
  end
end
