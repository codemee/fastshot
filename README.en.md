# FastShot

[繁體中文](README.md) | [English](README.en.md)

FastShot is a Python desktop screenshot utility focused on global shortcuts, a persistent system tray, tabbed editing, and fast copy/save workflows. Windows and macOS are currently supported. See [Cross-Platform Notes](docs/cross-platform.en.md) for platform permissions and acceptance guidance.

## Current Status

- Windows: Core features are implemented and have been manually tested and refined.
- macOS: Quartz global shortcuts, screen capture, focused-window capture, window/control selection, and cursor capture are implemented.
- Linux: Only the base architecture and some shared capabilities exist; Linux is not currently a primary target.

## Quick Start

Run the release without installing it:

```powershell
uvx --from "fastshot @ git+https://github.com/codemee/fastshot.git@v0.0.2" fastshot
```

The first run downloads packages and creates a uv cache environment. Later runs reuse that cache. Use `uvx` for evaluation and `uv tool install` for regular use.

Install the release from GitHub:

```powershell
uv tool install "fastshot @ git+https://github.com/codemee/fastshot.git@v0.0.2"
fastshot
```

Upgrade an installed version:

```powershell
uv tool upgrade fastshot
```

Install the latest development version from `main`:

```powershell
uv tool install --force "fastshot @ git+https://github.com/codemee/fastshot.git@main"
```

Run from a source checkout:

```powershell
uv sync
uv run fastshot
```

FastShot starts with its editor hidden and remains in the system tray. Double-click the tray icon to show the editor; use the tray context menu to exit.

The theme button cycles through Follow System, Light, and Dark. The language button cycles through Follow System, Traditional Chinese, and English. Both choices are persisted. Toolbar tooltips follow the selected language and include shortcuts where available.
The keyboard icon opens the global capture-shortcut settings for all four capture modes. Each shortcut can use Ctrl, Shift, Option/Alt, and an A–Z letter; Shift must be combined with Ctrl or Option/Alt. **Use defaults** restores the default combinations in the panel. Changes are persisted only after OK successfully registers every shortcut; Cancel keeps the active settings unchanged.

Images can also be added by drag-and-drop or clipboard paste. A dropped image opens under its full file name, retains its source path, and is saved back after editing. Pasted images create new unsaved tabs using the screenshot timestamp naming format. Paste uses `Ctrl+V` on Windows/Linux and `Command+V` on macOS.

## Capture Shortcuts

- `Alt+Shift+A`: Capture the focused window
- `Alt+Shift+R`: Capture a rectangular region
- `Alt+Shift+F`: Capture the full screen
- `Alt+Shift+W`: Select and capture a window or control

On macOS, replace `Alt` with `Option`. On first use, grant Screen Recording and Accessibility permissions when prompted; FastShot may need to be restarted afterward.

Editor shortcuts:

- `Alt+P`: Freehand pen
- `Alt+L`: Line
- `Alt+A`: Arrow
- `Alt+R`: Rectangle
- `Alt+T`: Text
- `Alt+M`: Mosaic
- `Alt+C`: Line width and color
- `Ctrl++` / `Ctrl+=`: Zoom in
- `Ctrl+-`: Zoom out
- `Ctrl+0`: Reset zoom

## Project Docs

- [PRD](PRD.en.md): Original product requirements.
- [Architecture](docs/architecture.en.md): Project structure, modules, and data flow.
- [Cross-Platform Notes](docs/cross-platform.en.md): Windows/macOS/Linux differences and platform acceptance guidance.

## Development

```shell
uv sync
uv run pytest -q
uv run python -m compileall src tests
```

If FastShot is running, `compileall` may occasionally fail because an executable or `__pycache__` file is locked. Stop FastShot and rerun the command.
