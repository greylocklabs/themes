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
        # Terminals and editors take a softer text color than the app, when the palette has one.
        return self.terminal.get("foreground", self.colors["text"])

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
        "accent_text": c["accent-text"], "accent_edge": c["accent-edge"], "selection": t.selection,
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
    # secondary colors the Build agent's name, prompt border and spinner.
    "primary": "accent", "secondary": "magenta", "accent": "cyan", "error": "red",
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
                        "terminal": t.terminal, "roles": roles(t), "slack": slack_colors(t)}
    return {"json/callie.json": json.dumps(body, indent=2) + "\n"}


def tuicr(t):
    r = roles(t)
    keys = {
        "panel_bg": "bg", "bg_highlight": "surface_alt", "fg_primary": "fg", "fg_secondary": "muted",
        "fg_dim": "faint", "diff_add": "green", "diff_add_bg": "added_bg", "diff_del": "red",
        "diff_del_bg": "removed_bg", "diff_context": "fg", "diff_hunk_header": "blue",
        "expanded_context_fg": "faint", "syntax_add_bg": "added_bg", "syntax_del_bg": "removed_bg",
        "file_added": "green", "file_modified": "yellow", "file_deleted": "red",
        "file_renamed": "magenta", "reviewed": "green", "pending": "yellow",
        "comment_note": "blue", "comment_suggestion": "cyan", "comment_issue": "red",
        "comment_praise": "green", "border_focused": "accent", "border_unfocused": "border",
        "status_bar_bg": "surface", "cursor_color": "accent", "cursor_line_bg": "surface",
        "branch_name": "magenta", "help_indicator": "faint", "message_info_fg": "bg",
        "message_info_bg": "blue", "message_warning_fg": "bg", "message_warning_bg": "yellow",
        "message_error_fg": "bg", "message_error_bg": "red", "update_badge_fg": "accent_text",
        "update_badge_bg": "accent", "mode_fg": "accent_text", "mode_bg": "accent",
    }
    lines = [f"# {t.title}: {HEADER.format(file=t.file)}"]
    lines += [f'{k} = "{r[v]}"' for k, v in keys.items()]
    return {f"tuicr/{t.name}.toml": "\n".join(lines) + "\n"}


def herdr(t):
    """A [theme] section for herdr's config.toml: its terminal theme with Callie's accent and rows."""
    r = roles(t)
    # overlay0 and overlay1 draw the scrollbars' tracks and thumbs, and dim text.
    r["overlay0"] = mix(t.bg, r["comment"], 0.5)
    r["overlay1"] = mix(t.bg, r["comment"], 0.75)
    keys = {
        "accent": "accent", "text": "fg", "subtext0": "muted", "panel_bg": None,
        "sidebar_bg": "bg", "active_row_bg": "surface_alt", "selection_bg": "selection",
        "surface0": "surface_alt", "surface1": "border", "surface_dim": "surface",
        "overlay0": "overlay0", "overlay1": "overlay1", "mauve": "magenta", "green": "green",
        "yellow": "yellow", "red": "red", "blue": "blue", "teal": "cyan", "peach": "yellow",
    }
    lines = [f"# {t.title}: {HEADER.format(file=t.file)}",
             "# Replace the [theme] section of ~/.config/herdr/config.toml with this.",
             "[theme]", 'name = "terminal"', "", "[theme.custom]"]
    for key, role in keys.items():
        lines.append(f'{key} = "reset"' if role is None else f'{key} = "{r[role]}"')
    return {f"herdr/{t.name}.toml": "\n".join(lines) + "\n"}


def claude_code(t):
    """A Claude Code custom theme, for ~/.claude/themes/."""
    import json
    r = roles(t)
    term = t.terminal
    # Pastel stand-ins for the subagent colors Callie has no ANSI slot for.
    purple, orange = (("#c6b3ef", "#ebb898") if t.variant == "dark" else ("#6f58a6", "#9a5c2e"))
    overrides = {
        "claude": r["accent"], "claudeShimmer": term["bright-magenta"], "text": r["fg"],
        "inverseText": r["bg"], "inactive": r["comment"], "inactiveShimmer": r["muted"],
        "subtle": r["border"], "suggestion": r["magenta"],
        # Draws dialog borders, and code in Claude's replies, which reads best warm.
        "permission": r["yellow"], "permissionShimmer": term["bright-yellow"],
        "remember": r["cyan"], "success": r["green"], "error": r["red"], "warning": r["yellow"],
        "warningShimmer": term["bright-yellow"], "merged": r["magenta"],
        "promptBorder": r["comment"], "promptBorderShimmer": r["muted"], "planMode": r["cyan"],
        "autoAccept": r["magenta"], "bashBorder": r["accent"], "ide": r["blue"],
        "fastMode": r["yellow"], "fastModeShimmer": term["bright-yellow"],
        "diffAdded": r["added_bg"], "diffRemoved": r["removed_bg"],
        "diffAddedDimmed": mix(t.bg, term["green"], 0.08), "diffRemovedDimmed": mix(t.bg, term["red"], 0.08),
        "diffAddedWord": r["added_hl"], "diffRemovedWord": r["removed_hl"],
        "userMessageBackground": r["surface"], "userMessageBackgroundHover": r["surface_alt"],
        "bashMessageBackgroundColor": r["surface"], "memoryBackgroundColor": r["surface"],
        "selectionBg": r["selection"], "composerSidebarBackground": r["surface"],
        "rate_limit_fill": r["accent"], "rate_limit_empty": r["border"],
        "briefLabelYou": r["accent"], "briefLabelClaude": r["magenta"],
        "red_FOR_SUBAGENTS_ONLY": r["red"], "blue_FOR_SUBAGENTS_ONLY": r["blue"],
        "green_FOR_SUBAGENTS_ONLY": r["green"], "yellow_FOR_SUBAGENTS_ONLY": r["yellow"],
        "purple_FOR_SUBAGENTS_ONLY": purple, "orange_FOR_SUBAGENTS_ONLY": orange,
        "pink_FOR_SUBAGENTS_ONLY": r["accent"], "cyan_FOR_SUBAGENTS_ONLY": r["cyan"],
        # Tokens the docs leave out: background tasks and shells, the system spinner, the
        # mascot, and the ultrathink rainbow.
        "background": r["magenta"], "claudeBlue_FOR_SYSTEM_SPINNER": r["accent"],
        "claudeBlueShimmer_FOR_SYSTEM_SPINNER": term["bright-magenta"],
        "professionalBlue": r["magenta"], "chromeYellow": r["yellow"], "effortUltra": r["accent"],
        "clawd_body": r["accent"], "clawd_background": r["bg"],
        "rainbow_red": r["red"], "rainbow_orange": orange, "rainbow_yellow": r["yellow"],
        "rainbow_green": r["green"], "rainbow_blue": r["blue"], "rainbow_indigo": purple,
        "rainbow_violet": r["magenta"], "rainbow_red_shimmer": term["bright-red"],
        "rainbow_orange_shimmer": mix(orange, "#ffffff", 0.25),
        "rainbow_yellow_shimmer": term["bright-yellow"], "rainbow_green_shimmer": term["bright-green"],
        "rainbow_blue_shimmer": term["bright-blue"], "rainbow_indigo_shimmer": mix(purple, "#ffffff", 0.25),
        "rainbow_violet_shimmer": term["bright-magenta"],
    }
    body = {"name": t.title, "base": t.variant, "overrides": overrides}
    return {f"claude-code/{t.name}.json": json.dumps(body, indent=2) + "\n"}


def slack_colors(t):
    """Slack's sidebar theme: ten colors pasted as one comma-separated line."""
    r = roles(t)
    order = ["bg", "surface_alt", "accent", "accent_text", "surface_alt", "fg", "green", "red",
             "edge", "fg"]
    return ",".join(r[k] for k in order)


def slack(t):
    return {f"slack/{t.name}.txt": slack_colors(t) + "\n"}


def discord(t):
    """A flavor of refact0r's Midnight theme for Vencord or BetterDiscord, in Callie's colors."""
    r, term = roles(t), t.terminal

    def scale(color, toward):
        return [mix(color, toward, a) for a in (0.0, 0.12, 0.24, 0.36, 0.48)]

    lines = [
        "/**", f" * @name {t.title}", f" * @description {t.title}, from greylocklabs/themes, on the midnight theme.",
        " * @author Greylock Labs", " * @website https://greylocklabs.org/brand/",
        " * @source https://github.com/greylocklabs/themes", "*/",
        f"/* {HEADER.format(file=t.file)} */",
        "@import url('https://refact0r.github.io/midnight-discord/build/midnight.css');", "",
        ":root {", "    --colors: on;",
        f"    --text-0: {r['accent_text']};", f"    --text-1: {t.colors['text']};", f"    --text-2: {r['fg']};",
        f"    --text-3: {r['muted']};", f"    --text-4: {r['faint']};",
        f"    --text-5: {mix(r['bg'], r['faint'], 0.5)};",
        f"    --bg-1: {r['border']};", f"    --bg-2: {r['surface_alt']};", f"    --bg-3: {r['surface']};",
        f"    --bg-4: {r['bg']};",
        f"    --hover: color-mix(in srgb, {r['muted']} 8%, transparent);",
        f"    --active: color-mix(in srgb, {r['muted']} 16%, transparent);",
        f"    --active-2: color-mix(in srgb, {r['muted']} 24%, transparent);",
        "    --message-hover: color-mix(in srgb, black 10%, transparent);",
    ]
    for i, c in enumerate(scale(r["accent"], r["bg"]), 1):
        lines.append(f"    --accent-{i}: {c};")
    lines.append("    --accent-new: var(--accent-2);")
    hues = {"red": "red", "green": "green", "blue": "blue", "yellow": "yellow", "purple": "magenta"}
    for name, role in hues.items():
        for i, c in enumerate(scale(term[f"bright-{role}"] if t.variant == "dark" else r[role], r["bg"]), 1):
            lines.append(f"    --{name}-{i}: {c};")
    lines.append("}")
    return {f"discord/{t.name}.theme.css": "\n".join(lines) + "\n"}


def lazygit(t):
    """The gui.theme section of lazygit's config.yml."""
    r = roles(t)
    theme = {
        "activeBorderColor": [r["accent"], "bold"], "inactiveBorderColor": [r["border"]],
        "searchingActiveBorderColor": [r["yellow"], "bold"], "optionsTextColor": [r["blue"]],
        "selectedLineBgColor": [r["surface_alt"]], "inactiveViewSelectedLineBgColor": [r["surface"]],
        "cherryPickedCommitFgColor": [r["accent_text"]], "cherryPickedCommitBgColor": [r["cyan"]],
        "markedBaseCommitFgColor": [r["accent_text"]], "markedBaseCommitBgColor": [r["yellow"]],
        "unstagedChangesColor": [r["red"]], "defaultFgColor": [r["fg"]],
    }
    lines = [f"# {t.title}: {HEADER.format(file=t.file)}", "gui:", "  theme:"]
    for key, value in theme.items():
        lines.append(f"    {key}:")
        lines += [f'      - "{v}"' for v in value]
    return {f"lazygit/{t.name}.yml": "\n".join(lines) + "\n"}


def gh_dash(t):
    """The theme section of gh-dash's config.yml; it needs every color set."""
    r = roles(t)
    colors = {
        "text": {"primary": r["fg"], "secondary": r["muted"], "inverted": r["accent_text"],
                 "faint": r["faint"], "warning": r["yellow"], "success": r["green"],
                 "error": r["red"], "actor": r["magenta"]},
        "background": {"selected": r["surface_alt"]},
        "border": {"primary": r["accent"], "secondary": r["border"], "faint": r["hairline"]},
        "icon": {"newcontributor": r["cyan"], "contributor": r["blue"],
                 "collaborator": r["magenta"], "member": r["magenta"], "owner": r["accent"],
                 "unknownrole": r["faint"]},
    }
    lines = [f"# {t.title}: {HEADER.format(file=t.file)}", "theme:", "  colors:"]
    for group, values in colors.items():
        lines.append(f"    {group}:")
        lines += [f'      {k}: "{v}"' for k, v in values.items()]
    return {f"gh-dash/{t.name}.yml": "\n".join(lines) + "\n"}


YOUTUBE = {
    "--yt-spec-base-background": "bg", "--yt-spec-raised-background": "surface",
    "--yt-spec-menu-background": "surface", "--yt-spec-inverted-background": "fg",
    "--yt-spec-additive-background": "surface_alt", "--yt-spec-general-background-a": "bg",
    "--yt-spec-general-background-b": "surface", "--yt-spec-general-background-c": "surface_alt",
    "--yt-spec-brand-background-solid": "bg", "--yt-spec-brand-background-primary": "bg",
    "--yt-spec-brand-background-secondary": "surface", "--yt-spec-snackbar-background": "surface_alt",
    "--yt-spec-badge-chip-background": "surface_alt", "--yt-spec-button-chip-background-hover": "border",
    "--yt-spec-10-percent-layer": "border", "--yt-spec-outline": "border",
    "--yt-spec-text-primary": "fg", "--yt-spec-text-primary-inverse": "bg",
    "--yt-spec-text-secondary": "muted", "--yt-spec-text-disabled": "faint",
    "--yt-spec-icon-active-other": "muted", "--yt-spec-icon-inactive": "faint",
    "--yt-spec-icon-disabled": "faint", "--yt-spec-call-to-action": "accent",
    "--yt-spec-call-to-action-inverse": "accent", "--yt-spec-brand-link-text": "accent",
    "--yt-spec-themed-blue": "accent", "--yt-spec-suggested-action": "surface_alt",
    "--yt-spec-static-brand-red": "accent", "--yt-spec-red-indicator": "accent",
    "--yt-spec-error-indicator": "red", "--yt-spec-themed-green": "green",
}


def youtube(dark, light):
    """CSS for YouTube Enhancer's custom CSS box: Callie in YouTube's dark mode, Callie Light otherwise."""
    # YouTube sets its colors on html[dark] and on inner [dark] elements, so the variables go on
    # the same selectors; scope prefixes the rules for the player and selection.
    def block(t, selector, scope):
        r = roles(t)
        out = [f"{selector} {{"] + [f"  {k}: {r[v]};" for k, v in YOUTUBE.items()] + ["}"]
        out += [f"{scope} .ytp-play-progress, {scope} .ytp-swatch-background-color {{",
                f"  background: {r['accent']} !important;", "}",
                f"{scope} .ytp-load-progress {{ background: {r['border']} !important; }}",
                f"{scope} ::selection {{ background: {r['selection']}; color: {r['fg']}; }}"]
        return "\n".join(out)

    text = (f"/* {HEADER.format(file='callie.toml and callie-light.toml')} */\n"
            "/* Callie in YouTube's dark appearance, Callie Light in its light one. */\n"
            + block(dark, "html[dark], html[dark] [dark]", "html[dark]") + "\n"
            + block(light, "html:not([dark])", "html:not([dark])") + "\n")

    # Enhancer for YouTube's custom theme replaces its built-in dark themes, so this one is
    # always dark, sets its accent variable, and draws thin scrollbars in it.
    r = roles(dark)
    enhancer = (f"/* {HEADER.format(file='callie.toml')} */\n"
                "/* Callie for Enhancer for YouTube's custom theme box; always dark. */\n"
                + block(dark, "html:root, [dark]", "html") + "\n"
                + f"html {{\n  --efyt-accent-color: {r['accent']};\n  --main-color: {r['accent']};\n}}\n"
                + "* {\n"
                + f"  scrollbar-color: {mix(r['bg'], r['comment'], 0.5)} transparent !important;\n"
                + "  scrollbar-width: thin !important;\n}\n")
    return {"youtube/callie.css": text, "youtube/enhancer-for-youtube.css": enhancer}


def gogh(t):
    """The YAML that Gogh and iTerm2-Color-Schemes take, which most terminals' theme lists come from."""
    lines = [f"# {HEADER.format(file=t.file)}", f'name: "{t.title}"',
             'author: "Greylock Labs (https://github.com/greylocklabs/themes)"',
             f'variant: "{t.variant}"', ""]
    lines += [f'color_{i:02d}: "{c}"' for i, c in enumerate(t.normal, 1)] + [""]
    lines += [f'color_{i:02d}: "{c}"' for i, c in enumerate(t.bright, 9)] + [""]
    lines += [f'background: "{t.bg}"', f'foreground: "{t.fg}"', f'cursor: "{t.cursor}"',
              f'cursor_text: "{t.cursor_text}"', f'selection: "{t.selection}"',
              f'selection_text: "{t.fg}"']
    return {f"gogh/{t.title}.yml": "\n".join(lines) + "\n"}


def gh_enhance(t):
    """A bubbletint theme file for gh-enhance's ENHANCE_THEME. gh-enhance draws focus in
    bright blue, so the blue slots carry Callie's pink."""
    import json
    r, term = roles(t), t.terminal
    body = {
        "display_name": t.title, "id": t.name, "dark": t.variant == "dark",
        "fg": r["fg"], "bg": r["bg"], "selection_bg": r["selection"], "cursor": r["accent"],
        "black": term["black"], "red": r["red"], "green": r["green"], "yellow": r["yellow"],
        "blue": r["magenta"], "purple": r["magenta"], "cyan": r["cyan"], "white": term["white"],
        "bright_black": term["bright-black"], "bright_red": term["bright-red"],
        "bright_green": r["green"], "bright_yellow": term["bright-yellow"],
        "bright_blue": r["accent"], "bright_purple": term["bright-magenta"],
        "bright_cyan": term["bright-cyan"], "bright_white": term["bright-white"],
    }
    return {f"gh-enhance/{t.name}.json": json.dumps(body, indent=2) + "\n"}


TMTHEME_SCOPES = [
    ("Comment", "comment, punctuation.definition.comment", "comment", "italic"),
    ("String", "string, punctuation.definition.string", "green", ""),
    ("Escape", "constant.character.escape, string.regexp", "accent", ""),
    ("Constant", "constant, constant.numeric, constant.language, support.constant", "yellow", ""),
    ("Keyword", "keyword, keyword.control, storage, storage.type, storage.modifier", "magenta", ""),
    ("Operator", "keyword.operator, punctuation", "muted", ""),
    ("Function", "entity.name.function, support.function, meta.function-call", "blue", ""),
    ("Type", "entity.name.type, entity.name.class, support.type, support.class", "cyan", ""),
    ("Parameter", "variable.parameter", "fg", "italic"),
    ("Built-in variable", "variable.language", "red", ""),
    ("Tag", "entity.name.tag", "magenta", ""),
    ("Attribute", "entity.other.attribute-name", "blue", ""),
    ("Heading", "markup.heading, entity.name.section", "accent", "bold"),
    ("Bold", "markup.bold", "fg", "bold"),
    ("Italic", "markup.italic", "fg", "italic"),
    ("Link", "markup.underline.link, string.other.link", "blue", "underline"),
    ("Code", "markup.raw, markup.inline.raw", "green", ""),
    ("Quote", "markup.quote", "muted", "italic"),
    ("Inserted", "markup.inserted", "green", ""),
    ("Deleted", "markup.deleted", "red", ""),
    ("Changed", "markup.changed", "blue", ""),
    ("Diff header", "meta.diff.header, meta.diff.range, meta.diff.index", "accent", ""),
    ("Invalid", "invalid", "red", "underline"),
]


def tmtheme(t):
    """A TextMate theme, which syntect-based tools such as Codex and bat read."""
    from xml.sax.saxutils import escape
    r = roles(t)

    def entry(name, scope, settings):
        body = "".join(f"<key>{k}</key><string>{escape(v)}</string>" for k, v in settings.items())
        head = (f"<key>name</key><string>{escape(name)}</string><key>scope</key>"
                f"<string>{escape(scope)}</string>") if name else ""
        return f"    <dict>{head}<key>settings</key><dict>{body}</dict></dict>"

    items = [entry("", "", {"background": r["bg"], "foreground": r["fg"], "caret": r["accent"],
                            "selection": r["selection"], "lineHighlight": r["surface"],
                            "gutterForeground": r["faint"], "invisibles": r["border"]})]
    for name, scope, role, style in TMTHEME_SCOPES:
        settings = {"foreground": r[role]}
        if style:
            settings["fontStyle"] = style
        items.append(entry(name, scope, settings))
    text = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
        f"<!-- {HEADER.format(file=t.file)} -->",
        '<plist version="1.0">', "<dict>",
        f"  <key>name</key><string>{t.title}</string>",
        "  <key>settings</key>", "  <array>", *items, "  </array>",
        "</dict>", "</plist>", ""])
    return {f"tmtheme/{t.name}.tmTheme": text}


PORTS = [kitty, konsole, ghostty, alacritty, foot, wezterm, tuicr, herdr, claude_code, slack, discord, lazygit, gh_dash, gh_enhance, gogh, tmtheme, preview]


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
    for port in (opencode, neovim, css, palette_json, youtube):
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
