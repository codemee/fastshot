# Installing the macOS app

[繁體中文](install-macos.md) | [English](install-macos.en.md)

FShot is distributed as an arm64 DMG containing `FShot.app` and an Applications shortcut. It supports Apple Silicon Macs only; no Intel Mac build is provided.

This personal-project build has no Apple Developer ID signature and is not notarized by Apple. The packaging tool may add a technical ad-hoc signature to internal Apple Silicon binaries, but that is not a trusted publisher signature and does not remove Gatekeeper warnings.

## Download and install

1. Download the arm64 DMG only from [FShot GitHub Releases](https://github.com/codemee/fshot/releases).
2. Verify it against `SHA256SUMS.txt`:

```bash
shasum -a 256 FShot-*-macos-*.dmg
```

3. Open the DMG and drag `FShot.app` to Applications.
4. If the first launch is blocked, dismiss the message and open **System Settings → Privacy & Security**.
5. Select **Open Anyway** beside the FShot security message, confirm, and launch it again.

Do not use a command that removes quarantine attributes as the normal installation method. After checking the official source and checksum, use macOS's Open Anyway override instead.

## Screen Recording and Accessibility

FShot needs macOS permissions for capture, window detection, and global shortcuts:

1. Allow FShot under **System Settings → Privacy & Security → Screen Recording**.
2. Allow FShot under **Accessibility**.
3. Quit FShot completely and reopen it.

Because the App has no formal signature, macOS may treat a replacement build as a different program. An update can require another Gatekeeper approval or renewed Screen Recording and Accessibility permissions.

## Updates

The packaged app checks GitHub Releases. When a new version is available it opens the download page and never replaces the unsigned App automatically. Download and verify the new DMG, replace the old `FShot.app` in Applications, and grant permissions again if macOS no longer recognizes them.
