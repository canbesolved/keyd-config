# AGENTS.md

## What this repo is

A personal [keyd](https://github.com/rvaiya/keyd) config (Linux key remapping daemon) for a laptop's built-in keyboard (`[ids] 0001:0001`). It is installed by copying `default.conf` to `/etc/keyd/default.conf` and running `sudo keyd reload`.

The layout has three parts:

- **Base (`[main]`)**: home-row mods (tap for the letter, hold for Meta/Alt/Ctrl/Shift on `A S D F` and `J K L ;`), `CapsLock` = Esc on tap / Caps layer on hold, `Right Alt` = AltGr layer on hold.
- **`[caps_layer]`**: vim-style arrows, page up/down, Enter/Backspace/Delete, left-hand modifiers, keyboard-layout switch, dictation toggle.
- **`[altgr_layer]`**: KDE desktop switching, volume, media, brightness, lock and suspend.

## Files

| Path | Purpose |
| --- | --- |
| `default.conf` | The keyd config, the single source of truth |
| `README.md` | Human description of the layout, embeds the image |
| `assets/layout.svg` | Generated keyboard picture (committed, never edit by hand) |
| `scripts/draw_layout.py` | Generates `assets/layout.svg` from `default.conf` |
| `scripts/hooks/regenerate-layout.sh` | Agent hook that reruns the generator after edits |
| `.cursor/hooks.json`, `.claude/settings.json` | Hook registration for Cursor and Claude Code |
| `build/` | Intermediate files (`keymap.yaml`, `laptop60.json`), gitignored |

## Editing `default.conf`

- Keep one mapping per line (`key = action`) and group related mappings under a `#` comment, as the existing file does. keyd only supports full-line comments.
- After changing mappings, update the matching layer section in `README.md` so the text and the picture agree.
- The image must be regenerated and committed together with the config change (see below).

## Keyboard image generation

The picture is drawn with [keymap-drawer](https://github.com/caksoylar/keymap-drawer). keymap-drawer cannot parse keyd configs, so `scripts/draw_layout.py` does it:

1. Parses `default.conf`: `[main]` becomes the Base layer and every other section becomes its own layer (`[ids]` and `[global]` are skipped).
2. Converts actions to legends: `overload`/`overloadt`/`overloadt2`/`overloadi` become tap-hold keys, `layer(x)` shows the modifier, shortcut combos such as `M-f1` get a friendly name with the shortcut shown small on top, plain keys get short labels. The key that activates a layer is highlighted as held in that layer.
3. Writes a 61-key 60% ANSI physical layout (`build/laptop60.json`, QMK `info.json` format) and the keymap (`build/keymap.yaml`), then runs `keymap draw` to produce `assets/layout.svg`. The SVG follows the viewer's light/dark theme.

Regenerate manually with:

```bash
uv run scripts/draw_layout.py
```

`uv` installs Python 3.12+ and keymap-drawer on first run. Without uv: `pip install keymap-drawer && python3 scripts/draw_layout.py` (Python 3.12+).

### Labels

Config-specific wording lives in the tables at the top of `scripts/draw_layout.py`:

- `ACTION_LABELS`: short legends for keyd key names (`pagedown` -> `PgDn`).
- `COMBO_LABELS`: names for shortcut combos (`M-l` -> `Lock`). Add an entry when you map a new combo, otherwise the raw shortcut is shown.
- `LAYER_HOLD_LABELS` / `LAYER_TITLES`: hold legend and heading for each layer. Add entries when you add a section.

Rules that keep the picture readable: plain text only (no emoji), at most about 6 characters per word, one word per friendly name (keymap-drawer wraps on spaces). The script prints a warning for labels that are too long and for config keys that are not on the drawn layout.

The bottom row is a generic laptop layout and may not match the physical keyboard exactly.

### Hooks

Both Cursor (`afterFileEdit`) and Claude Code (`PostToolUse` on `Edit|Write|MultiEdit`) run `scripts/hooks/regenerate-layout.sh`. It regenerates the image only when `default.conf` or `scripts/draw_layout.py` was edited and never blocks the edit. Edits made outside an agent do not trigger it; run the generator yourself before committing.
