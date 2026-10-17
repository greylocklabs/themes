#!/usr/bin/env python3
"""Writes every port under ports/ from the palettes, or with --check fails if one is out of date.

Each palette other than callie.toml inherits what it leaves out from callie.toml, as in the apps.
"""
import argparse
import pathlib
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ANSI = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
HEADER = "Generated from palettes/{file} by scripts/generate.py; edit the palette, not this file."


def load(name):
    base = tomllib.loads((ROOT / "palettes/callie.toml").read_text())
    if name == "callie":
        return base
    own = tomllib.loads((ROOT / f"palettes/{name}.toml").read_text())
    return {section: {**base.get(section, {}), **own.get(section, {})}
            for section in base.keys() | own.keys()}


class Theme:
    def __init__(self, name):
        self.name = name
        self.file = f"{name}.toml"
        data = load(name)
        self.title = data["theme"]["name"]
        self.variant = data["theme"]["variant"]
        self.colors = data["colors"]
        self.terminal = data["terminal"]
        self.normal = [self.terminal[c] for c in ANSI]
        self.bright = [self.terminal[f"bright-{c}"] for c in ANSI]

    @property
    def fg(self):
        return self.colors["text"]

    @property
    def bg(self):
        return self.colors["background"]

    @property
    def cursor(self):
        return self.colors["accent"]

    @property
    def cursor_text(self):
        return self.colors["accent-text"]

    @property
    def selection(self):
        return self.terminal["selection"]


def rgb(color):
    return ",".join(str(int(color[i:i + 2], 16)) for i in (1, 3, 5))


def mix(a, b, amount):
    """a moved toward b by amount, in sRGB, for tinted backgrounds."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02x}" for x, y in zip(pa, pb))


def roles(t):
    """What each kind of text is drawn in, shared by the editor ports."""
    c, term = t.colors, t.terminal
    return {
        "fg": t.fg, "bg": t.bg, "muted": c["text-muted"], "faint": c["text-faint"],
        "surface": c["surface"], "surface_alt": c["surface-alt"], "border": c["border"],
        "hairline": c["hairline"], "edge": c["edge"], "accent": c["accent"],
        "accent_text": c["accent-text"], "selection": t.selection,
        "red": term["red"], "green": term["green"], "yellow": term["yellow"], "blue": term["blue"],
        "magenta": term["magenta"], "cyan": term["cyan"], "comment": term["bright-black"],
        "added_bg": mix(t.bg, term["green"], 0.16), "removed_bg": mix(t.bg, term["red"], 0.16),
        "changed_bg": mix(t.bg, term["blue"], 0.14), "added_hl": mix(t.bg, term["green"], 0.32),
        "removed_hl": mix(t.bg, term["red"], 0.32),
    }


def kitty(t):
    lines = [f"# vim:ft=kitty", f"# {t.title}: {HEADER.format(file=t.file)}", "",
             f"foreground {t.fg}", f"background {t.bg}",
             f"selection_foreground {t.fg}", f"selection_background {t.selection}",
             f"cursor {t.cursor}", f"cursor_text_color {t.cursor_text}",
             f"url_color {t.cursor}",
             f"active_border_color {t.colors['accent']}",
             f"inactive_border_color {t.colors['border']}",
             f"bell_border_color {t.terminal['yellow']}",
             f"active_tab_foreground {t.cursor_text}", f"active_tab_background {t.colors['accent']}",
             f"inactive_tab_foreground {t.colors['text-muted']}",
             f"inactive_tab_background {t.colors['surface-alt']}",
             f"tab_bar_background {t.colors['edge']}",
             f"mark1_foreground {t.bg}", f"mark1_background {t.terminal['blue']}",
             f"mark2_foreground {t.bg}", f"mark2_background {t.terminal['magenta']}",
             f"mark3_foreground {t.bg}", f"mark3_background {t.terminal['cyan']}", ""]
    lines += [f"color{i} {c}" for i, c in enumerate(t.normal + t.bright)]
    return {f"kitty/{t.name}.conf": "\n".join(lines) + "\n"}


def konsole(t):
    out = [f"# {HEADER.format(file=t.file)}", "", "[General]", f"Description={t.title}",
           "Opacity=1", "Wallpaper=", ""]

    def section(name, color):
        out.extend([f"[{name}]", f"Color={rgb(color)}", ""])

    section("Background", t.bg)
    section("BackgroundFaint", t.bg)
    section("BackgroundIntense", t.bg)
    for i, (normal, bright) in enumerate(zip(t.normal, t.bright)):
        section(f"Color{i}", normal)
        section(f"Color{i}Faint", normal)
        section(f"Color{i}Intense", bright)
    section("Foreground", t.fg)
    section("ForegroundFaint", t.colors["text-muted"])
    section("ForegroundIntense", t.fg)
    file = t.title.replace(" ", "")
    return {f"konsole/{file}.colorscheme": "\n".join(out).rstrip() + "\n"}


def ghostty(t):
    lines = [f"# {HEADER.format(file=t.file)}"]
    lines += [f"palette = {i}={c}" for i, c in enumerate(t.normal + t.bright)]
    lines += [f"background = {t.bg}", f"foreground = {t.fg}", f"cursor-color = {t.cursor}",
              f"cursor-text = {t.cursor_text}", f"selection-background = {t.selection}",
              f"selection-foreground = {t.fg}"]
    return {f"ghostty/{t.title}": "\n".join(lines) + "\n"}


def alacritty(t):
    def table(name, colors):
        return [f"[colors.{name}]"] + [f'{c} = "{v}"' for c, v in zip(ANSI, colors)] + [""]

    lines = [f"# {t.title}: {HEADER.format(file=t.file)}", "", "[colors.primary]",
             f'background = "{t.bg}"', f'foreground = "{t.fg}"', "", "[colors.cursor]",
             f'text = "{t.cursor_text}"', f'cursor = "{t.cursor}"', "", "[colors.selection]",
             f'text = "{t.fg}"', f'background = "{t.selection}"', ""]
    lines += table("normal", t.normal) + table("bright", t.bright)
    return {f"alacritty/{t.name}.toml": "\n".join(lines).rstrip() + "\n"}


def foot(t):
    bare = lambda c: c.lstrip("#")  # noqa: E731
    lines = [f"# {t.title}: {HEADER.format(file=t.file)}", "", "[colors]",
             f"foreground={bare(t.fg)}", f"background={bare(t.bg)}",
             f"cursor={bare(t.cursor_text)} {bare(t.cursor)}",
             f"selection-foreground={bare(t.fg)}", f"selection-background={bare(t.selection)}"]
    lines += [f"regular{i}={bare(c)}" for i, c in enumerate(t.normal)]
    lines += [f"bright{i}={bare(c)}" for i, c in enumerate(t.bright)]
    return {f"foot/{t.name}.ini": "\n".join(lines) + "\n"}


def wezterm(t):
    quoted = lambda colors: "[" + ", ".join(f'"{c}"' for c in colors) + "]"  # noqa: E731
    lines = [f"# {HEADER.format(file=t.file)}", "", "[colors]", f'foreground = "{t.fg}"',
             f'background = "{t.bg}"', f'cursor_bg = "{t.cursor}"', f'cursor_fg = "{t.cursor_text}"',
             f'cursor_border = "{t.cursor}"', f'selection_fg = "{t.fg}"',
             f'selection_bg = "{t.selection}"', f"ansi = {quoted(t.normal)}",
             f"brights = {quoted(t.bright)}", "", "[metadata]", f'name = "{t.title}"',
             'origin_url = "https://github.com/greylocklabs/themes"']
    return {f"wezterm/{t.title}.toml": "\n".join(lines) + "\n"}


def preview(t):
    """A swatch card: the text on the background, then each ANSI color, normal above bright."""
    w, cell, pad = 8 * 72, 72, 24
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w + 2 * pad}" height="{2 * cell + 96}" '
             f'viewBox="0 0 {w + 2 * pad} {2 * cell + 96}">',
             f'<rect width="100%" height="100%" rx="16" fill="{t.bg}"/>',
             f'<text x="{pad}" y="44" font-family="Nunito, sans-serif" font-size="22" font-weight="800" '
             f'fill="{t.fg}">{t.title}</text>',
             f'<text x="{w + pad}" y="44" text-anchor="end" font-family="Nunito, sans-serif" font-size="16" '
             f'fill="{t.colors["text-muted"]}">{t.variant}</text>']
    for row, colors in enumerate((t.normal, t.bright)):
        for i, c in enumerate(colors):
            parts.append(f'<rect x="{pad + i * cell + 4}" y="{68 + row * cell}" width="{cell - 8}" '
                         f'height="{cell - 8}" rx="11" fill="{c}"/>')
    parts.append("</svg>")
    return {f"previews/{t.name}.svg": "\n".join(parts) + "\n"}


OPENCODE = {
    "primary": "accent", "secondary": "blue", "accent": "magenta", "error": "red",
    "warning": "yellow", "success": "green", "info": "cyan", "text": "fg", "textMuted": "muted",
    "selectedListItemText": "accent_text", "background": "bg", "backgroundPanel": "surface",
    "backgroundElement": "surface_alt", "backgroundMenu": "surface", "border": "border",
    "borderActive": "accent", "borderSubtle": "hairline", "diffAdded": "green",
    "diffRemoved": "red", "diffContext": "muted", "diffHunkHeader": "blue",
    "diffHighlightAdded": "green", "diffHighlightRemoved": "red", "diffAddedBg": "added_bg",
    "diffRemovedBg": "removed_bg", "diffContextBg": "surface", "diffLineNumber": "faint",
    "diffAddedLineNumberBg": "added_hl", "diffRemovedLineNumberBg": "removed_hl",
    "markdownText": "fg", "markdownHeading": "accent", "markdownLink": "blue",
    "markdownLinkText": "cyan", "markdownCode": "green", "markdownBlockQuote": "muted",
    "markdownEmph": "yellow", "markdownStrong": "red", "markdownHorizontalRule": "faint",
    "markdownListItem": "accent", "markdownListEnumeration": "cyan", "markdownImage": "blue",
    "markdownImageText": "cyan", "markdownCodeBlock": "fg", "syntaxComment": "comment",
    "syntaxKeyword": "magenta", "syntaxFunction": "blue", "syntaxVariable": "fg",
    "syntaxString": "green", "syntaxNumber": "yellow", "syntaxType": "cyan",
    "syntaxOperator": "muted", "syntaxPunctuation": "muted",
}


def opencode(dark, light):
    import json
    d, l = roles(dark), roles(light)
    theme = {key: {"dark": d[role], "light": l[role]} for key, role in OPENCODE.items()}
    body = {"$schema": "https://opencode.ai/theme.json", "theme": theme}
    return {"opencode/callie.json": json.dumps(body, indent=2) + "\n"}


# Highlight groups as (fg, bg, style) in terms of roles(); None leaves a part unset.
NEOVIM = {
    "Normal": ("fg", "bg", ""), "NormalNC": ("fg", "bg", ""), "NormalFloat": ("fg", "surface", ""),
    "FloatBorder": ("border", "surface", ""), "FloatTitle": ("accent", "surface", "bold"),
    "Cursor": ("accent_text", "accent", ""), "CursorLine": (None, "surface", ""),
    "CursorColumn": (None, "surface", ""), "ColorColumn": (None, "surface", ""),
    "CursorLineNr": ("accent", None, "bold"), "LineNr": ("faint", None, ""),
    "SignColumn": (None, "bg", ""), "FoldColumn": ("faint", "bg", ""),
    "Folded": ("muted", "surface_alt", ""), "VertSplit": ("border", None, ""),
    "WinSeparator": ("border", None, ""), "Visual": (None, "selection", ""),
    "Search": ("accent_text", "yellow", ""), "IncSearch": ("accent_text", "accent", "bold"),
    "CurSearch": ("accent_text", "accent", "bold"), "MatchParen": ("accent", "surface_alt", "bold"),
    "Pmenu": ("fg", "surface", ""), "PmenuSel": ("accent_text", "accent", "bold"),
    "PmenuSbar": (None, "surface_alt", ""), "PmenuThumb": (None, "border", ""),
    "StatusLine": ("fg", "surface_alt", ""), "StatusLineNC": ("faint", "surface", ""),
    "TabLine": ("muted", "surface", ""), "TabLineSel": ("accent_text", "accent", "bold"),
    "TabLineFill": (None, "edge", ""), "WinBar": ("muted", None, ""),
    "NonText": ("faint", None, ""), "Whitespace": ("hairline", None, ""),
    "EndOfBuffer": ("bg", None, ""), "Directory": ("blue", None, ""),
    "Title": ("accent", None, "bold"), "ErrorMsg": ("red", None, "bold"),
    "WarningMsg": ("yellow", None, ""), "MoreMsg": ("green", None, ""),
    "Question": ("blue", None, ""), "ModeMsg": ("fg", None, "bold"),
    "SpecialKey": ("faint", None, ""), "Conceal": ("faint", None, ""),
    "QuickFixLine": (None, "surface_alt", "bold"), "WildMenu": ("accent_text", "accent", ""),
    "DiffAdd": (None, "added_bg", ""), "DiffDelete": (None, "removed_bg", ""),
    "DiffChange": (None, "changed_bg", ""), "DiffText": (None, "added_hl", ""),
    "Added": ("green", None, ""), "Removed": ("red", None, ""), "Changed": ("blue", None, ""),
    "SpellBad": (None, None, "undercurl"), "SpellCap": (None, None, "undercurl"),
    "Comment": ("comment", None, "italic"), "Constant": ("yellow", None, ""),
    "String": ("green", None, ""), "Character": ("green", None, ""), "Number": ("yellow", None, ""),
    "Boolean": ("yellow", None, ""), "Float": ("yellow", None, ""), "Identifier": ("fg", None, ""),
    "Function": ("blue", None, ""), "Statement": ("magenta", None, ""),
    "Keyword": ("magenta", None, ""), "Conditional": ("magenta", None, ""),
    "Repeat": ("magenta", None, ""), "Label": ("magenta", None, ""),
    "Exception": ("magenta", None, ""), "Operator": ("muted", None, ""),
    "PreProc": ("accent", None, ""), "Include": ("magenta", None, ""), "Type": ("cyan", None, ""),
    "StorageClass": ("magenta", None, ""), "Structure": ("cyan", None, ""),
    "Special": ("accent", None, ""), "Delimiter": ("muted", None, ""),
    "Tag": ("blue", None, ""), "Underlined": ("blue", None, "underline"),
    "Todo": ("accent_text", "yellow", "bold"), "Error": ("red", None, ""),
    "@variable": ("fg", None, ""), "@variable.builtin": ("red", None, ""),
    "@variable.parameter": ("fg", None, "italic"), "@variable.member": ("fg", None, ""),
    "@property": ("fg", None, ""), "@constant": ("yellow", None, ""),
    "@constant.builtin": ("yellow", None, ""), "@module": ("cyan", None, ""),
    "@string": ("green", None, ""), "@string.escape": ("accent", None, ""),
    "@string.special": ("accent", None, ""), "@function": ("blue", None, ""),
    "@function.builtin": ("blue", None, ""), "@function.method": ("blue", None, ""),
    "@constructor": ("cyan", None, ""), "@keyword": ("magenta", None, ""),
    "@keyword.function": ("magenta", None, ""), "@keyword.return": ("magenta", None, ""),
    "@operator": ("muted", None, ""), "@punctuation": ("muted", None, ""),
    "@punctuation.bracket": ("muted", None, ""), "@punctuation.delimiter": ("muted", None, ""),
    "@type": ("cyan", None, ""), "@type.builtin": ("cyan", None, ""), "@tag": ("magenta", None, ""),
    "@tag.attribute": ("blue", None, ""), "@tag.delimiter": ("muted", None, ""),
    "@comment": ("comment", None, "italic"), "@markup.heading": ("accent", None, "bold"),
    "@markup.strong": (None, None, "bold"), "@markup.italic": (None, None, "italic"),
    "@markup.link": ("blue", None, "underline"), "@markup.link.label": ("cyan", None, ""),
    "@markup.raw": ("green", None, ""), "@markup.quote": ("muted", None, "italic"),
    "@markup.list": ("accent", None, ""), "@diff.plus": ("green", None, ""),
    "@diff.minus": ("red", None, ""), "@diff.delta": ("blue", None, ""),
    "DiagnosticError": ("red", None, ""), "DiagnosticWarn": ("yellow", None, ""),
    "DiagnosticInfo": ("cyan", None, ""), "DiagnosticHint": ("blue", None, ""),
    "DiagnosticOk": ("green", None, ""), "DiagnosticUnderlineError": (None, None, "undercurl"),
    "DiagnosticUnderlineWarn": (None, None, "undercurl"),
    "DiagnosticUnderlineInfo": (None, None, "undercurl"),
    "DiagnosticUnderlineHint": (None, None, "undercurl"),
    "LspReferenceText": (None, "surface_alt", ""), "LspReferenceRead": (None, "surface_alt", ""),
    "LspReferenceWrite": (None, "surface_alt", ""), "LspInlayHint": ("faint", None, "italic"),
    "GitSignsAdd": ("green", None, ""), "GitSignsChange": ("blue", None, ""),
    "GitSignsDelete": ("red", None, ""), "TelescopeNormal": ("fg", "surface", ""),
    "TelescopeBorder": ("border", "surface", ""), "TelescopeTitle": ("accent", None, "bold"),
    "TelescopeSelection": (None, "surface_alt", ""), "TelescopeMatching": ("accent", None, "bold"),
    "TelescopePromptPrefix": ("accent", None, ""), "BufferLineFill": (None, "edge", ""),
    "BufferLineBufferSelected": ("fg", None, "bold"), "BufferLineIndicatorSelected": ("accent", None, ""),
    "WhichKey": ("accent", None, ""), "WhichKeyGroup": ("blue", None, ""),
    "WhichKeyDesc": ("fg", None, ""), "IblIndent": ("hairline", None, ""),
    "IblScope": ("border", None, ""), "NeoTreeNormal": ("fg", "bg", ""),
    "NeoTreeDirectoryName": ("blue", None, ""), "NeoTreeGitModified": ("yellow", None, ""),
    "NvimTreeFolderName": ("blue", None, ""), "MiniStatuslineModeNormal": ("accent_text", "accent", "bold"),
    "BlinkCmpMenu": ("fg", "surface", ""), "BlinkCmpMenuBorder": ("border", "surface", ""),
    "BlinkCmpMenuSelection": ("accent_text", "accent", ""), "CmpItemAbbrMatch": ("accent", None, "bold"),
    "CmpItemKind": ("cyan", None, ""),
}
UNDERCURL = {"SpellBad": "red", "SpellCap": "yellow", "DiagnosticUnderlineError": "red",
             "DiagnosticUnderlineWarn": "yellow", "DiagnosticUnderlineInfo": "cyan",
             "DiagnosticUnderlineHint": "blue"}


def neovim(dark, light):
    def palette(t):
        r = roles(t)
        lines = []
        for group, (fg, bg, style) in NEOVIM.items():
            spec = []
            if fg:
                spec.append(f'fg = "{r[fg]}"')
            if bg:
                spec.append(f'bg = "{r[bg]}"')
            if group in UNDERCURL:
                spec.append(f'sp = "{r[UNDERCURL[group]]}"')
            spec += [f"{s} = true" for s in style.split()]
            lines.append(f'    ["{group}"] = {{ {", ".join(spec)} }},')
        ansi = ", ".join(f'"{c}"' for c in t.normal + t.bright)
        return "\n".join(lines), ansi

    dark_groups, dark_ansi = palette(dark)
    light_groups, light_ansi = palette(light)
    header = f"-- {HEADER.format(file='callie.toml and callie-light.toml')}"
    text = f"""{header}
-- Callie for Neovim: dark or light, following 'background'. Callie Light is
-- also :colorscheme callie-light.
local themes = {{
  dark = {{
    ansi = {{ {dark_ansi} }},
    groups = {{
{dark_groups}
    }},
  }},
  light = {{
    ansi = {{ {light_ansi} }},
    groups = {{
{light_groups}
    }},
  }},
}}

vim.cmd("highlight clear")
if vim.fn.exists("syntax_on") == 1 then
  vim.cmd("syntax reset")
end
vim.o.termguicolors = true
local theme = themes[vim.o.background] or themes.dark
vim.g.colors_name = vim.o.background == "light" and "callie-light" or "callie"
for group, spec in pairs(theme.groups) do
  vim.api.nvim_set_hl(0, group, spec)
end
for i, color in ipairs(theme.ansi) do
  vim.g["terminal_color_" .. (i - 1)] = color
end
"""
    light_file = f"""{header}
vim.o.background = "light"
vim.cmd("runtime colors/callie.lua")
"""
    return {"../colors/callie.lua": text, "../colors/callie-light.lua": light_file}


def css(dark, light):
    """CSS variables, light by default and dark when the system or data-theme asks."""
    def block(t, indent):
        pad = " " * indent
        return "\n".join(f"{pad}--callie-{k.replace('_', '-')}: {v};" for k, v in roles(t).items())

    text = f"""/* {HEADER.format(file='callie.toml and callie-light.toml')} */
:root {{
{block(light, 2)}
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
{block(dark, 4)}
  }}
}}
:root[data-theme="dark"] {{
{block(dark, 2)}
}}
"""
    return {"css/callie.css": text}


def palette_json(dark, light):
    import json
    body = {"generated": HEADER.format(file="callie.toml and callie-light.toml")}
    for t in (dark, light):
        body[t.name] = {"name": t.title, "variant": t.variant, "colors": t.colors,
                        "terminal": t.terminal, "roles": roles(t)}
    return {"json/callie.json": json.dumps(body, indent=2) + "\n"}


PORTS = [kitty, konsole, ghostty, alacritty, foot, wezterm, preview]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a port is out of date")
    args = parser.parse_args()

    names = sorted(p.stem for p in (ROOT / "palettes").glob("*.toml")
                   if "terminal" in tomllib.loads(p.read_text()))
    files = {}
    for name in names:
        theme = Theme(name)
        for port in PORTS:
            files.update(port(theme))
    # The editor ports hold both variants in one file.
    for port in (opencode, neovim, css, palette_json):
        files.update(port(Theme("callie"), Theme("callie-light")))

    stale = []
    for path, text in sorted(files.items()):
        target = (ROOT / "ports" / path).resolve()
        if target.exists() and target.read_text() == text:
            continue
        stale.append(path)
        if not args.check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
    if args.check and stale:
        sys.exit("out of date, run scripts/generate.py: " + ", ".join(stale))
    if not args.check:
        print("\n".join(f"wrote {(ROOT / 'ports' / p).resolve().relative_to(ROOT)}" for p in stale)
              or "ports are up to date")


if __name__ == "__main__":
    main()
