# Cross-Platform Notes

[繁體中文](cross-platform.md) | [English](cross-platform.en.md)

Most FastShot UI code uses reusable PySide6 components. Capture, global shortcuts, cursor extraction, window selection, permissions, and some clipboard behavior remain platform-specific.

Themes are shared through `ThemeManager` and Qt system color hints. Language is shared through `LanguageManager`; macOS prioritizes `AppleLanguages`, while other platforms use the Qt locale. Tab close buttons follow platform placement and use FastShot's high-contrast icon. Windows places the dirty marker left of the title.

Image drag/drop and paste use Qt `QMimeData`, `QUrl`, and clipboard APIs. On macOS, verify Finder local-file URLs, HEIC/HEIF decoder availability, and source-file write access in sandboxed builds.

## Current Platform State

### Windows

- Global shortcuts use `RegisterHotKey` and consume `WM_HOTKEY`.
- The toolbar keyboard icon configures the four capture shortcuts and the repeat action; Windows probes `RegisterHotKey` conflicts before applying them.
- Repeat Previous Capture defaults to `Ctrl+Shift+Q`, is configurable, and preserves the previous region or selected window/control target.
- Full-screen/region capture uses `mss` with Pillow `ImageGrab` fallback.
- Region capture freezes the virtual desktop before showing the selector, preserving transient menus that disappear on focus loss.
- Focused-window bounds use DWM extended frame bounds.
- Window/control selection prefers UI Automation with HWND fallback.
- Real cursor images are converted from Win32 handles best-effort.
- Tray, editor, clipboard, save, crop, and drawing workflows are implemented.

### macOS

- Quartz event taps consume `Ctrl+Shift+A/R/F/W`.
- The shortcut listener supports user-configured Ctrl/Shift/Option plus A–Z combinations, persisted with `QSettings`.
- Screen Recording permission is checked/requested.
- Accessibility `AXFocusedWindow` is preferred; Core Graphics window fallback avoids transient browser popups.
- Accessibility hit testing finds the smallest valid element under the pointer and clamps results to the owning window.
- Current `NSCursor` image, hotspot, and position are included best-effort.
- Shared Qt tray, editor, clipboard, and save workflows are used.

First launch requests Accessibility permission; first capture requests Screen Recording permission. The project currently runs through `uv`/`uvx` and is not packaged as a standalone macOS app, so the entries under **System Settings → Privacy & Security → Accessibility / Screen Recording** usually belong to the app that launched the `uv` command rather than to FastShot. This is commonly Terminal, iTerm2, Warp, or an IDE host. Enable both permissions for the app that actually launches FastShot; after changing them, fully quit and reopen that host app, then run FastShot again. Without Accessibility permission, global shortcuts and control selection may be unavailable, while window hit testing falls back best-effort.

### Linux

Linux is not currently a primary target. X11 and Wayland differ substantially in global shortcuts, capture permissions, and window discovery.

## Platform Boundaries

- Global hotkeys currently live in `app.py`; a future `hotkeys.py` could expose per-platform backends.
- Capture orchestration currently lives in `capture.py`; future work can split shared flow from `platforms/windows.py` and `platforms/macos.py`.
- Window/control selection uses UI Automation on Windows and Accessibility on macOS.
- Cursor backends should return equivalent image, hotspot, and screen-position data.
- macOS permission checks must remain explicit; Windows currently has no centralized permission flow.

## macOS Implementation Layout

- `platforms/macos.py`: permissions, Core Graphics/Accessibility window queries, cursor, and shortcuts.
- `capture.py`: shared capture flow and platform delegation.
- `app.py`: Windows native filter, macOS event tap, and fallback lifecycle.

## Manual Acceptance Checklist

- Shortcuts trigger capture and are not forwarded to the focused application.
- The shortcut panel opens with the active values; **Use defaults** changes only the pending panel values, OK applies and persists them, and Cancel leaves the active settings unchanged.
- On macOS, custom Ctrl/Shift/Option plus letter combinations trigger the intended capture mode and remain configured after restart.
- Immediate and delayed capture resolve the target first and capture the live image at countdown completion.
- Full-screen, region, focused-window, and selected window/control capture work.
- Browser transient URLs/tooltips are not mistaken for the focused window.
- Escape cancels region/window selection.
- Include Cursor captures the current real pointer.
- New captures appear at the editor's top-left.
- Clipboard content pastes into common applications.
- PNG/JPG save works.
- Dropped images open under their original name, start clean, and save edits back to the source.
- Saved tabs rename their source file inline with Windows/Linux `F2`, macOS `Return`, or a double-click; existing files are not overwritten and the extension is preserved.
- Pasted images and pasted file-manager images create new timestamp-named tabs.
- Minimize/hide, tray double-click, and tray Exit work.
