# macOS 應用程式安裝

[繁體中文](install-macos.md) | [English](install-macos.en.md)

FShot 以 arm64 DMG 發布，內含 `FShot.app` 與「Applications」捷徑，僅支援 Apple Silicon Mac，不提供 Intel Mac 版本。

這是個人專案版本，沒有 Apple Developer ID 簽章，也沒有經過 Apple notarization。打包工具可能為 Apple Silicon 內部二進位加入技術性的 ad-hoc signature，但這不是可信任的發行者簽章，無法消除 Gatekeeper 警告。

## 下載與安裝

1. 只從 [FShot GitHub Releases](https://github.com/codemee/fshot/releases) 下載 arm64 DMG。
2. 依 `SHA256SUMS.txt` 驗證下載檔：

```bash
shasum -a 256 FShot-*-macos-*.dmg
```

3. 開啟 DMG，將 `FShot.app` 拖曳至 Applications。
4. 第一次開啟若被阻擋，先關閉提示，再前往「系統設定 → 隱私權與安全性」。
5. 在 FShot 的安全性訊息旁選擇「仍要打開」，再次確認後啟動。

請勿把移除 quarantine 屬性的終端機指令當作一般安裝步驟。只有在確認官方下載來源及雜湊後，才應使用 macOS 提供的「仍要打開」覆寫機制。

## 螢幕錄製與輔助使用

FShot 的截圖、視窗辨識及全域快捷鍵需要 macOS 權限：

1. 在「系統設定 → 隱私權與安全性 → 螢幕錄製」允許 FShot。
2. 在「輔助使用」允許 FShot。
3. 完全結束 FShot，再重新啟動。

因為 App 沒有正式簽章，macOS 在更新替換 App 後可能把它視為不同程式，要求再次確認 Gatekeeper 或重新授予上述權限。

## 更新

打包版會檢查 GitHub Releases。發現新版時會開啟下載頁面，不會自動替換未簽章 App。下載新 DMG、驗證雜湊後，以新版 `FShot.app` 取代 Applications 中的舊版；若權限失效，請重新授權並重啟。
