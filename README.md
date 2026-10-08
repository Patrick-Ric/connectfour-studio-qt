# ConnectFour Studio (Qt)

*Open-source Connect Four with 15 levels, 20 boards, tournament mode, match statistics and perfect real-time analysis.*

A free, offline desktop program for Connect Four — play against the computer,
analyze positions, and run engine-vs-engine matches. This is the **Qt 6
(PySide6) port** of the original Tkinter version, with the same features,
menus and keyboard shortcuts.

- **Engine:** BitBully by Markus Thill (Python module `bitbully`, C++ core)
- **GUI:** Python + Qt 6 / PySide6 (+ Pillow)
- **License:** GNU AGPL v3 — source code freely available

## Features

- 14 computer levels (1 Random … 14 Perfect) + 0 Loser joke level + 2 custom user levels with own (p, s, w)
- Live evaluation: winner + stones to the end, nodes, time, book/computed source
- Modes: Human-Computer, 2 players, Computer-Computer playout, Computer-Computer match
- 20 boards with matching stones (mouse wheel / PageUp-PageDown to browse)
- Session score vs. the engine, quicksave, random positions, GUI and help in 6 languages (German, English, French, Spanish, Dutch, Italian)

## Install & Start

### Linux AppImage (no install needed)

```bash
chmod +x ConnectFour_Studio_Qt-x86_64.AppImage
./ConnectFour_Studio_Qt-x86_64.AppImage
```

Requires glibc ≥ 2.28 (Ubuntu 20.04+, Debian 10+, Fedora 29+); install
libfuse2 if needed (or run with `--appimage-extract-and-run`). The AppImage
brings its own Python 3.14 and the needed Qt libraries; on X11 it falls back to
bundled `libxcb-cursor`/xcb-util libraries if the system does not have them.

### From source

Requires 64-bit Python 3.10–3.14 (`bitbully` ships wheels for CPython
3.10–3.14 on 64-bit Windows/Linux). No Tkinter needed anymore.

Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python connectfour_studio_qt.py
```

Windows (PowerShell or cmd):

```bat
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python connectfour_studio_qt.py
```

Optional: `connectfour_studio_qt.py position.4gp` loads and evaluates a position at start.

## Keyboard

- `1-7` play column, `Arrow Left/Right` undo/redo, `Arrow Up/Down` first/last move
- `PageUp/PageDown` or mouse wheel over the board browse boards
- `F1` help, `F3/F4` quick save/load, `F5` engine move, `F6` evaluate all moves, `F7` permanent analysis
- Help window: `Ctrl+F` find, `Ctrl +/-/0` or `Ctrl+wheel` text zoom

## User data

Quicksave (`quicksave.4gp`), language (`lang.cfg`) and settings
(`settings.json`: view options, stone set, computer level, last folder of the
file dialogs) are stored in

- `$CFS_USER_DIR` if set, otherwise
- Linux/macOS: `~/.config/connectfour-studio-qt` (respects `$XDG_CONFIG_HOME`)
- Windows: `%APPDATA%\ConnectFour Studio Qt`

File dialogs start in the last used folder, otherwise in your home folder.
`.4gp` files are plain digit strings of the played columns (e.g. `4433221`)
and are fully compatible with the Tkinter version.

## Project layout

- `connectfour_studio_qt.py` — start script
- `cfs_core/` — GUI-independent core
  - `game.py` board/history, `.4gp` format, winning lines
  - `engine.py` BitBully move selection per level, iterative analysis, random positions
  - `levels.py` level table (p, s, w), labels, Elo
  - `match.py` match scoring and session score
  - `sets.py` stone sets (image loading + measuring with Pillow)
  - `lang.py` UI strings in 6 languages (the former `cfs_lang`)
  - `help_content.py` help/info texts (the former `cfs_help` content)
  - `paths.py` program/user paths, settings
- `cfs_qt/` — Qt user interface
  - `main_window.py` main window, menus, shortcuts, game flow, threads
  - `board.py` board widget (QPainter)
  - `dialogs.py` random position, match, info and help dialogs
  - `tiles.py` image → QPixmap cache, `app.py` application start
- `data/images/set1..set20` — boards and stones
- `tests/` — pytest (game logic, engine, `.4gp` compatibility, offscreen GUI smoke test)
- `packaging/linux` — AppImage build, `packaging/windows` — PyInstaller build
- `FEATURES.md` — feature list of the Tk version, checked against this port
- `PORTING.md` — decisions taken during the Tk → Qt port

## Development

```bash
.venv/bin/pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest
```

Self test of the packaged program (opens the main window and every dialog
offscreen, plays one engine move, exits):

```bash
CFS_SMOKE_TEST=1 QT_QPA_PLATFORM=offscreen ./ConnectFour_Studio_Qt-x86_64.AppImage
```

### Build the Linux AppImage

```bash
packaging/linux/build_appimage.sh
```

Downloads (once, into `build/cache`) the python-appimage base
(CPython 3.14, manylinux_2_28), appimagetool and its runtime, and the
xcb-util-cursor source; installs the requirements, strips everything not
needed (only QtCore/QtGui/QtWidgets and their dependencies, no Tk, no pip),
checks the content (`verify_appdir.py`) and writes
`ConnectFour_Studio_Qt-x86_64.AppImage`.

### Build for Windows

On Windows with 64-bit Python 3.10–3.14:

```bat
packaging\windows\build_windows.bat
```

See `packaging/windows/README.md`.

## Credits

- Engine: **BitBully by Markus Thill** — https://markusthill.github.io/projects/0_bitbully/
- Opening book: `bitbully-databases` (`12-ply-dist`)
- GUI toolkit: Qt 6 via PySide6 (Qt for Python)
