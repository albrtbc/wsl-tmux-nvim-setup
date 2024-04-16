vim.g.mapleader = ','
vim.g.maplocalleader = ','

vim.opt.backspace = '2'
vim.opt.showcmd = true
vim.opt.laststatus = 2
vim.opt.autowrite = true
vim.opt.cursorline = true
vim.opt.autoread = true
vim.opt.wrap = false
vim.opt.mouse = ""

--setnowrap toggle
vim.api.nvim_set_keymap('n', '<leader>tw', ':set wrap!<CR>', {noremap = true, silent = true})

--use spaces for tabs
vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.shiftround = true
vim.opt.expandtab = true

--restore search
vim.keymap.set('n', '<leader>h', ':nohlsearch<CR>')
vim.api.nvim_set_keymap('v', 'p', '"_dP', {noremap = true})

--custom options
vim.cmd([[
    cmap w!! %!sudo tee > /dev/null %
    set history=700
    set autoread
]])

--custom typos mappings
vim.api.nvim_set_keymap('n', ':W', ':w', { noremap = true })
vim.api.nvim_set_keymap('n', ':Q', ':q', { noremap = true })
vim.api.nvim_set_keymap('n', 'q:', ':q', { noremap = true })
vim.api.nvim_set_keymap('n', ':WQ', ':wq', { noremap = true })
vim.api.nvim_set_keymap('n', ':wQ', ':wq', { noremap = true })
vim.api.nvim_set_keymap('n', ':Wq', ':wq', { noremap = true })
vim.api.nvim_set_keymap('n', ':Qa', ':qa', { noremap = true })
vim.api.nvim_set_keymap('n', ':QA', ':qa', { noremap = true })
vim.api.nvim_set_keymap('n', ':qA', ':qa', { noremap = true })

--tab identification
vim.api.nvim_set_keymap('n', '<S-Tab>', '<', { noremap = true })
vim.api.nvim_set_keymap('i', '<S-Tab>', '<Esc><<i', { noremap = true })
vim.api.nvim_set_keymap('v', '<S-Tab>', '<gv', { noremap = true })
vim.api.nvim_set_keymap('v', '<Tab>', '>gv', { noremap = true })

--options
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.showmatch = true
vim.opt.errorbells = false
vim.opt.visualbell = false
vim.opt.tm = 500
vim.opt.vb = true

--persistent undo
vim.opt.undodir = os.getenv('HOME') .. '/.nvim/undodir'
vim.opt.undofile = true
vim.opt.undolevels = 1000
vim.opt.undoreload = 10000

vim.opt.autoindent = true

--search for the visual selection cursor
vim.api.nvim_set_keymap('v', '*', ':call VisualSelection("f")<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('v', '#', ':call VisualSelection("b")<CR>', { noremap = true, silent = true })

--jumps to the last cursor position on file openning
vim.cmd([[
    autocmd BufReadPost *
        \ if line("'\"") > 0 && line("'\"") <= line("$") |
        \   exe "normal g'\"" |
        \ endif
]])

--WSL yank support
vim.opt.clipboard:append { 'unnamed', 'unnamedplus' }
if vim.fn.has('wsl') == 1 then
    vim.cmd([[
        augroup WSLClipboard
            autocmd!
            autocmd TextYankPost * if v:event.operator == 'y' && v:event.regname == '' | call system('clip.exe', @0) | endif
        augroup END
    ]])
end

