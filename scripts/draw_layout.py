#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["keymap-drawer>=0.23"]
# ///
"""Draw the keyd layout from default.conf as assets/layout.svg using keymap-drawer.

keymap-drawer has no keyd parser, so this script parses the keyd config itself,
writes a keymap-drawer YAML plus a QMK-style physical layout into build/, and
then runs `keymap draw` on them.

Usage: uv run scripts/draw_layout.py
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "default.conf"
BUILD = ROOT / "build"
LAYOUT_JSON = BUILD / "thinkpad14.json"
KEYMAP_YAML = BUILD / "keymap.yaml"
OUTPUT_SVG = ROOT / "assets" / "layout.svg"

MAX_LABEL_LEN = 6

# Lenovo ThinkPad T14 Gen 4 (US ANSI) keyboard, measured from a photo. Every
# key is a tuple (keyd key name, width, base legend) with an optional height
# and an optional absolute (x, y) position for keys that do not follow the row
# flow. The board is 14.6 units wide.
FN_H = 0.7
FN_SCALE = 0.974  # photo x positions were measured against a 15-unit board
ROW_Y = [0.0, 0.85, 1.85, 2.85, 3.85, 4.85]
ARROW_X = 12.0
ARROW_H = 0.5

# Function row: Esc, three groups of four F keys, then Home/End/Insert/Delete.
FN_ROW = [
    ("esc", 1.1, "Esc", 0.0),
    *[
        (f"f{n}", 0.78, f"F{n}", x)
        for n, x in enumerate(
            [1.25, 2.07, 2.88, 3.7, 4.6, 5.42, 6.24, 7.06, 8.0, 8.82, 9.63, 10.45],
            start=1,
        )
    ],
    ("home", 0.8, "Home", 11.4),
    ("end", 0.8, "End", 12.2),
    ("insert", 0.8, "Ins", 13.05),
    ("delete", 1.15, "Del", 13.85),
]

ROWS: list[list[tuple]] = [
    [
        (name, round(w * FN_SCALE, 3), label, FN_H, round(x * FN_SCALE, 3), ROW_Y[0])
        for name, w, label, x in FN_ROW
    ],
    [("grave", 1, "`")]
    + [(c, 1, c) for c in "1234567890"]
    + [("minus", 1, "-"), ("equal", 1, "="), ("backspace", 1.6, "Bksp")],
    [("tab", 1.4, "Tab")]
    + [(c, 1, c.upper()) for c in "qwertyuiop"]
    + [("leftbrace", 1, "["), ("rightbrace", 1, "]"), ("backslash", 1.2, "\\")],
    [("capslock", 1.6, "Caps")]
    + [(c, 1, c.upper()) for c in "asdfghjkl"]
    + [("semicolon", 1, ";"), ("apostrophe", 1, "'"), ("enter", 2, "Enter")],
    [("leftshift", 2.2, "Shift")]
    + [(c, 1, c.upper()) for c in "zxcvbnm"]
    + [("comma", 1, ","), ("dot", 1, "."), ("slash", 1, "/"), ("rightshift", 2.4, "Shift")],
    [
        ("fn", 1.03, "Fn"),
        ("leftcontrol", 1.26, "Ctrl"),
        ("leftmeta", 1, "Meta"),
        ("leftalt", 1, "Alt"),
        ("space", 5.06, ""),
        ("rightalt", 0.9, "AltGr"),
        ("sysrq", 0.89, "PrtSc"),
        ("rightcontrol", 0.86, "Ctrl"),
        # Inverted-T arrow cluster: PgUp / Up / PgDn above Left / Down / Right.
        ("pageup", 0.77, "PgUp", ARROW_H, ARROW_X, ROW_Y[5]),
        ("up", 0.75, "↑", ARROW_H, ARROW_X + 0.93, ROW_Y[5]),
        ("pagedown", 0.77, "PgDn", ARROW_H, ARROW_X + 1.83, ROW_Y[5]),
        ("left", 0.77, "←", ARROW_H, ARROW_X, ROW_Y[5] + ARROW_H),
        ("down", 0.75, "↓", ARROW_H, ARROW_X + 0.93, ROW_Y[5] + ARROW_H),
        ("right", 0.77, "→", ARROW_H, ARROW_X + 1.83, ROW_Y[5] + ARROW_H),
    ],
]

KEY_ALIASES = {
    "`": "grave",
    "-": "minus",
    "=": "equal",
    "[": "leftbrace",
    "]": "rightbrace",
    "\\": "backslash",
    ";": "semicolon",
    "'": "apostrophe",
    ",": "comma",
    ".": "dot",
    "/": "slash",
}

MODIFIER_LABELS = {
    "meta": "Meta",
    "alt": "Alt",
    "control": "Ctrl",
    "shift": "Shift",
    "altgr": "AltGr",
}

COMBO_PREFIXES = {"M": "Meta", "A": "Alt", "C": "Ctrl", "S": "Shift", "G": "AltGr"}

# Legends for keys that appear as actions (right-hand side of a mapping).
ACTION_LABELS = {
    "esc": "Esc",
    "leftmeta": "Meta",
    "enter": "Enter",
    "backspace": "Bksp",
    "delete": "Del",
    "tab": "Tab",
    "space": "Space",
    "left": "←",
    "down": "↓",
    "up": "↑",
    "right": "→",
    "pageup": "PgUp",
    "pagedown": "PgDn",
    "home": "Home",
    "end": "End",
    "insert": "Ins",
    "print": "PrtSc",
    "capslock": "Caps",
    "scrolllock": "ScrLk",
    "scrolldown": "ScrDn",
    "scrollup": "ScrUp",
    "mute": "Mute",
    "volumedown": "Vol−",
    "volumeup": "Vol+",
    "playpause": "Play",
    "nextsong": "Next",
    "previoussong": "Prev",
    "brightnessdown": "Brt−",
    "brightnessup": "Brt+",
}

# Shorter key names used inside the small shortcut text shown on top of a key.
SHORTCUT_KEY_LABELS = {"space": "Spc", "backspace": "Bksp", "delete": "Del"}

# Friendly names for shortcut combos; the shortcut itself is shown small on top.
# keymap-drawer wraps legends on spaces, so keep each name a single word.
COMBO_LABELS = {
    "M-l": "Lock",
    "M-/": "Susp",
    "M-space": "Lang",
    "A-space": "Run",
    "M-]": "Tabs",
    "C-w": "Close",
    "C-r": "Reload",
    "A-f4": "Term",
    "C-c": "Copy",
    "C-v": "Paste",
    "C-x": "Cut",
}

# Hold legends for keyd layers (sections other than [main]).
LAYER_HOLD_LABELS = {
    "space_layer": "Space L",
    "altgr_layer": "AltGr L",
}

# Diagram headings; unknown sections get an auto-generated title.
LAYER_TITLES = {
    "main": "Base (tap = key, hold = modifier)",
    "space_layer": "Space layer (hold Space)",
    "altgr_layer": "AltGr layer (hold Right Alt)",
}

SKIPPED_SECTIONS = {"ids", "global"}

BASE_LABELS = {spec[0]: spec[2] for row in ROWS for spec in row}


@dataclass
class Legend:
    t: str
    h: str | None = None
    s: str | None = None
    hold_target: str | None = None


def warn(msg: str) -> None:
    print(f"draw_layout: warning: {msg}", file=sys.stderr)


def normalize_key(key: str) -> str:
    return KEY_ALIASES.get(key, key)


def key_label(key: str) -> str:
    key = normalize_key(key)
    if key in ACTION_LABELS:
        return ACTION_LABELS[key]
    if key in BASE_LABELS and BASE_LABELS[key]:
        return BASE_LABELS[key]
    if re.fullmatch(r"f\d+", key):
        return key.upper()
    return key.capitalize()


def hold_label(target: str) -> str:
    if target in MODIFIER_LABELS:
        return MODIFIER_LABELS[target]
    return LAYER_HOLD_LABELS.get(target, target.replace("_", " ").capitalize())


def split_args(inner: str) -> list[str]:
    args, depth, current = [], 0, ""
    for ch in inner:
        if ch == "," and depth == 0:
            args.append(current.strip())
            current = ""
            continue
        depth += ch == "("
        depth -= ch == ")"
        current += ch
    args.append(current.strip())
    return args


def parse_action(action: str) -> Legend:
    action = action.strip()
    call = re.fullmatch(r"(\w+)\((.*)\)", action)
    if call:
        name, args = call.group(1), split_args(call.group(2))
        if name in ("overload", "overloadt", "overloadt2"):
            tap = parse_action(args[1])
            return Legend(t=tap.t, s=tap.s, h=hold_label(args[0]), hold_target=args[0])
        if name == "overloadi":
            tap, hold = parse_action(args[0]), parse_action(args[1])
            return Legend(t=tap.t, s=tap.s, h=hold.h or hold.t, hold_target=hold.hold_target)
        if name == "macro" and " " not in args[0]:
            return parse_action(args[0])
        if name == "macro2":
            return parse_action(args[2])
        if name == "layer":
            return Legend(t=hold_label(args[0]))
        if name == "oneshot":
            return Legend(t=hold_label(args[0]), s="1-shot")
        warn(f"unsupported action {action!r}, drawn as its name")
        return Legend(t=name)

    combo = re.fullmatch(r"((?:[MACSG]-)+)(.+)", action)
    if combo:
        mods = [COMBO_PREFIXES[p] for p in combo.group(1).split("-") if p]
        key = normalize_key(combo.group(2))
        shortcut = "+".join(mods + [SHORTCUT_KEY_LABELS.get(key, key_label(key))])
        return Legend(t=COMBO_LABELS.get(action, shortcut), s=shortcut)

    return Legend(t=key_label(action))


def parse_config(text: str) -> dict[str, dict[str, Legend]]:
    sections: dict[str, dict[str, Legend]] = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        header = re.fullmatch(r"\[([^\]]+)\]", line)
        if header:
            current = header.group(1).split(":")[0]
            if current not in SKIPPED_SECTIONS:
                sections.setdefault(current, {})
            continue
        if current is None or current in SKIPPED_SECTIONS:
            continue
        mapping = re.fullmatch(r"(\S+)\s*=\s*(.+)", line)
        if not mapping:
            warn(f"cannot parse line in [{current}]: {line!r}")
            continue
        key = normalize_key(mapping.group(1))
        if key not in BASE_LABELS:
            warn(f"[{current}] {key} is not on the drawn keyboard, skipped")
            continue
        sections[current][key] = parse_action(mapping.group(2))
    return sections


def layer_title(section: str) -> str:
    return LAYER_TITLES.get(section, section.replace("_", " ").capitalize())


def to_yaml_key(legend: Legend) -> str | dict:
    for line in legend.t.split():
        if len(line) > MAX_LABEL_LEN:
            warn(f"label {legend.t!r} is longer than {MAX_LABEL_LEN} characters")
    if legend.h is None and legend.s is None:
        return legend.t
    return {k: v for k, v in (("t", legend.t), ("h", legend.h), ("s", legend.s)) if v is not None}


def build_layers(sections: dict[str, dict[str, Legend]]) -> dict[str, list[list]]:
    main = sections.get("main", {})
    activators: dict[str, list[str]] = {}
    for key, legend in main.items():
        if legend.hold_target in sections and legend.hold_target != "main":
            activators.setdefault(legend.hold_target, []).append(key)

    layers = {}
    for section, mappings in [("main", main)] + [(s, m) for s, m in sections.items() if s != "main"]:
        rows = []
        for row in ROWS:
            drawn = []
            for key, _, base, *_ in row:
                if key in mappings:
                    drawn.append(to_yaml_key(mappings[key]))
                elif section != "main" and key in activators.get(section, []):
                    drawn.append({"t": base, "type": "held"})
                else:
                    drawn.append(base if section == "main" else "")
            rows.append(drawn)
        layers[layer_title(section)] = rows
    return layers


def physical_layout() -> dict:
    keys = []
    for row_y, row in zip(ROW_Y, ROWS):
        x = 0.0
        for _, w, _, *geometry in row:
            h = geometry[0] if geometry else 1
            if len(geometry) == 3:
                key_x, key_y = geometry[1:]
            else:
                key_x, key_y = x, row_y
                x += w
            key = {"x": round(key_x, 3), "y": round(key_y, 3)}
            if w != 1:
                key["w"] = round(w, 3)
            if h != 1:
                key["h"] = h
            keys.append(key)
    return {"layouts": {"LAYOUT": {"layout": keys}}}


def main() -> None:
    sections = parse_config(CONFIG.read_text())
    keymap = {
        "layout": {"qmk_info_json": str(LAYOUT_JSON.relative_to(ROOT)), "layout_name": "LAYOUT"},
        "draw_config": {"dark_mode": "auto"},
        "layers": build_layers(sections),
    }

    BUILD.mkdir(exist_ok=True)
    OUTPUT_SVG.parent.mkdir(exist_ok=True)
    LAYOUT_JSON.write_text(json.dumps(physical_layout(), indent=2) + "\n")
    KEYMAP_YAML.write_text(yaml.safe_dump(keymap, sort_keys=False, allow_unicode=True))

    subprocess.run(
        [sys.executable, "-W", "ignore::DeprecationWarning", "-m", "keymap_drawer", "draw", str(KEYMAP_YAML), "-o", str(OUTPUT_SVG)],
        cwd=ROOT,
        check=True,
    )
    print(f"draw_layout: wrote {OUTPUT_SVG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
