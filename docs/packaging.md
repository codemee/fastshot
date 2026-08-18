# Desktop Packaging

FShot uses PyInstaller for desktop packages. Builds must run on the target operating system.

## Local build

```powershell
uv sync
uv run python scripts/build_app.py
```

Windows produces `dist/FShot-<version>-windows-x64.exe`. Apple Silicon macOS produces `dist/FShot-<version>-macos-arm64.dmg` containing `FShot.app` and an Applications shortcut. Intel macOS is not supported.

Generated icons and Windows version resources live under `build/package-assets` and are not source files. The PyInstaller spec copies FShot package metadata so the frozen application title and update checker retain the installed version.

## GitHub Actions

Publishing a GitHub Release automatically builds Windows x64 and macOS arm64 packages, attaches them to that release, and uploads `SHA256SUMS.txt`. **Package desktop apps** can also be run manually with an existing tag or ref; enable **Attach artifacts to an existing matching GitHub Release** only when the supplied ref names an existing release tag.

The workflow does not use Authenticode, Apple Developer ID, or notarization credentials. See the platform installation guides for the resulting SmartScreen and Gatekeeper experience.
