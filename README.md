# Callie themes

The colors of [Callie](https://callieapp.org) and the other [Greylock Labs](https://greylocklabs.org)
apps, for your terminal, editor and projects: a dark **Callie** and a light **Callie Light**.

![Callie](ports/previews/callie.svg)
![Callie Light](ports/previews/callie-light.svg)

## Install

Each port has a file per variant under `ports/`.

- **kitty:** copy `ports/kitty/callie.conf` and `callie-light.conf` to `~/.config/kitty/`, and add
  `include callie.conf` to `kitty.conf`. To follow the desktop's light or dark setting, copy them
  as `dark-theme.auto.conf` and `light-theme.auto.conf` instead.
- **Konsole:** copy `ports/konsole/*.colorscheme` to `~/.local/share/konsole/`, then pick Callie in
  the profile's Appearance settings.
- **Ghostty:** copy `ports/ghostty/*` to `~/.config/ghostty/themes/`, and set
  `theme = light:Callie Light,dark:Callie`.
- **Alacritty:** add `general.import = ["/path/to/ports/alacritty/callie.toml"]` to
  `alacritty.toml`.
- **foot:** add `include=/path/to/ports/foot/callie.ini` to `foot.ini`.
- **WezTerm:** copy `ports/wezterm/*.toml` to `~/.config/wezterm/colors/`, and set
  `config.color_scheme = "Callie"`.

### Editors and apps

- **Neovim:** install this repository as a plugin, for example with lazy.nvim:
  `{ "greylocklabs/themes", name = "callie", priority = 1000, config = function() vim.cmd.colorscheme("callie") end }`.
  `callie` follows `background`, so `:set background=light` switches to Callie Light; `callie-light`
  sets it for you. It covers Treesitter, LSP and diagnostics, gitsigns, Telescope, bufferline,
  which-key, indent-blankline, neo-tree, nvim-tree, blink.cmp and nvim-cmp.
- **opencode:** copy `ports/opencode/callie.json` to `~/.config/opencode/themes/`, and set
  `"theme": "callie"` in `tui.json`. It follows the terminal's light or dark mode.
- **Programs that use the terminal's colors,** such as lazygit, follow whichever terminal theme
  is set. For ghzinga, set `theme = "terminal"`; for Claude Code, pick an "ANSI colors only" theme
  in `/theme`.

### For your own projects

- `ports/css/callie.css` sets the colors as `--callie-*` CSS variables: light by default, dark when
  the system prefers it, and either one with `data-theme="light"` or `"dark"` on the root element.
- `ports/json/callie.json` holds every color, ANSI color and role for both variants, for build
  scripts and tools that read the palette themselves.

## How it works

`palettes/` holds the theme files, the same ones Callie reads, plus a `[terminal]` section with
the 16 ANSI colors. Each hue sits at one OKLCH lightness and chroma per variant, so no color shouts
over the others, with red starting from Callie's danger color and magenta from its pink accent.
`callie-light.toml` takes whatever it leaves out from `callie.toml`.

`scripts/generate.py` writes every port and preview from the palettes. Edit a palette, run it,
and commit both; CI fails when a port is out of date.

Commit messages follow the shared conventional style, with a scope always required. Run
`npm install` and `git config core.hooksPath .githooks` to check them locally.
