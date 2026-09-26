# keyd config

Optimized layout designed to minimize hand movement and maximize productivity.

## Layers

- **HRM**: Modifiers (Meta, Alt, Ctrl, Shift) are placed directly on the home row (ASDF / JKL;) via dual-function keys. Tap for the character, hold for the modifier.
- **Caps Layer**: Turns `CapsLock` layer on hold or `Escape` when tapped
- **Right Alt (AltGr)**: Uses `Right Alt` on hold to access KDE desktop switching, media controls, and system actions

*Note: HRM use a custom timeout. A tap (< 150ms) registers as a character. Holding (> 200ms) or pressing in combination with another key registers as the modifier.*

## Caps Layer

**Navigation & Editing**
- `H`, `J`, `K`, `L` → `Left`, `Down`, `Up`, `Right`
- `U`, `I` → `Page Up`, `Page Down`
- `O` → `Backspace`
- `[` → `Delete`
- `;` → `Enter`

**Modifiers (Left Hand)**
- `A` → `Alt`
- `S` → `Shift`
- `D` → `Ctrl`

**System / Misc**
- `F` → `Meta + Space` (change keyboard layout)
- `M` → `ScrollLock` (voice input using voxtype)

## RightAlt layer

**Workspace & System (KDE)**
- `A`, `S`, `D`, `F` → `Meta + F1-F4` (switch Desktops 1-4)
- `O` → `Meta + L` (lock screen)
- `/` → `Meta + /` (suspend)

**Media & Brightness**
- `H` → Mute Audio
- `J`, `K` → Volume Down, Volume Up
- `L`, `;` → Brightness Down, Brightness Up

## Requirements

- Linux environment
- [keyd](https://github.com/rvaiya/keyd)
- KDE Plasma (for desktop switching and lock screen shortcuts)

## Installation

1. Install `keyd` from the [official repository](https://github.com/rvaiya/keyd).
2. Copy config file to `/etc/keyd/default.conf`:
   ```bash
   sudo cp default.conf /etc/keyd/
   ```
3. Reloda the `keyd` config:
   ```bash
   sudo keyd restart
   ```

## License

MIT
