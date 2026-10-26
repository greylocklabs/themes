# Repo notes - themes

Facts the review bot cannot infer from one pass over the diff. The philosophy, the finding categories, the workflow,
the scoring and the output format all live in the bot's base prompt; this file only refines them for this repo.

## What this repo is

The Callie and Callie Light colors for other software: terminals, editors, chat apps and the like. People copy the files
under `ports/` into their own setups, so a change here reaches them the next time they copy, with no release step.

| Path                  | What it is                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------- |
| `palettes/*.toml`     | The source of every color. `callie.toml` sets every key; other palettes inherit from it.    |
| `scripts/generate.py` | Writes every port from the palettes; `--check`, which CI runs, fails if one is out of date. |
| `ports/<tool>/`       | Generated files, one per variant, each with a header saying not to edit it.                 |
| `ports/previews/`     | The SVG previews the README shows, also generated.                                          |
| `colors/*.lua`        | The Neovim colorschemes, generated like the ports.                                          |

## What to check

- **Generated files are never edited by hand.** A change under `ports/` or `colors/` without the matching change to a
  palette or to `scripts/generate.py` is a finding; so is a generator change that leaves the ports stale, which CI
  catches but the review should name.
- **The palettes match the apps.** The keys `palettes/callie.toml` shares with greylocklabs/core's `themes/callie.toml`
  (and likewise for Callie Light) must keep the same values, so the ports look like the apps. The terminal colors
  (`foreground` and the ANSI colors) exist only here.
- **Each port's format.** A port must load in its tool: the right keys, file extension and syntax for that tool's
  current version. Name the tool's own documentation when a key looks wrong.
- **Contrast.** Text colors keep at least 4.5:1 against the background they sit on in each variant.
