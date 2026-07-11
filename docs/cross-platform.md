# Cross-Platform Notes

FastShot 的 UI 大部分使用 PySide6，可跨平台重用；但截圖、全域快捷鍵、游標、視窗選取與剪貼簿都是平台相依區域。macOS 實作時請優先處理本文件列出的邊界。

配色主題屬於跨平台共用 UI：`ThemeManager` 使用 Qt 系統配色提示與 `QSettings`，支援跟隨系統、淺色及深色模式。修改主題樣式或圖示時，應同時在 Windows 與 macOS 驗證系統配色偵測、即時切換與持久化。
介面語言同樣屬於跨平台共用 UI：`LanguageManager` 在 macOS 優先讀取使用者的 `AppleLanguages`，其他平台使用 Qt locale；繁體中文系統環境顯示繁中，其餘預設英文，並允許使用者手動覆寫。
頁籤關閉按鈕遵循平台位置：macOS 位於左側、Windows 位於右側，但使用 FastShot 自繪高對比圖示以確保淺色與深色主題皆清楚可見。未存檔狀態以標題後方、垂直置中的紅色方塊表示，不再修改標題文字。

## Current Platform State

### Windows

Windows 是目前主要實作平台。

已實作：

- 全域快捷鍵：`RegisterHotKey` 接收 `WM_HOTKEY`，避免快捷鍵送到焦點視窗。
- 全螢幕/矩形擷取：`mss`，失敗時 fallback 到 Pillow `ImageGrab`。
- 焦點視窗擷取：DWM `DWMWA_EXTENDED_FRAME_BOUNDS`，避免截到不可見 resize frame。
- 選取視窗/控制項：UI Automation 優先，傳統 HWND hit-test fallback。
- 真實游標貼圖：Win32 cursor handle best-effort 轉 RGBA bitmap，失敗不阻斷截圖。
- 系統匣、編輯器、剪貼簿、存檔、裁切與繪圖工具。

### macOS

已實作：

- Quartz event tap 全域快捷鍵，攔截並 consume `Option+Shift+A/R/F/W`。
- 透過 Screen Recording API 檢查並要求螢幕錄製權限。
- 優先使用 Accessibility `AXFocusedWindow` 擷取焦點視窗；失敗時才從前景程序的 Core Graphics 視窗選擇最大正常視窗，避免 Chrome 連結網址等 transient popup 被誤判為焦點視窗。
- 使用 Accessibility API hit-test 最小控制項，並將 bounds 限制在游標下視窗內；無效或未包含游標的結果會 fallback 至游標下視窗。
- 使用目前 `NSCursor` 圖像、hotspot 與游標座標貼入截圖。
- 共用 Qt 剪貼簿、系統匣、編輯器與存檔流程。

首次啟動會要求輔助使用權限，首次截圖會要求螢幕錄製權限。若系統設定已變更但功能仍不可用，請完全結束並重新啟動 FastShot。未授予輔助使用權限時，控制項選取與全域快捷鍵不可用；視窗 hit-test 仍會 best-effort fallback。

### Linux

Linux 尚未作為主要目標。Wayland/X11 差異很大，尤其是全域快捷鍵、截圖權限與視窗查詢。

## Platform Boundaries

跨平台工作應優先把以下能力抽象化，避免把平台分支散落在 UI 層：

- Global hotkeys
  - 目前在 `app.py`。
  - 建議後續抽出 `hotkeys.py`，依平台實作 Windows/macOS/Linux backend。

- Capture backend
  - 目前集中在 `capture.py`。
  - 建議拆成通用 `CaptureService` 加平台 backend，例如 `platforms/windows.py`、`platforms/macos.py`。

- Window/control selection
  - Windows 目前使用 UI Automation + HWND fallback。
  - macOS 應用 Accessibility API 提供同等的 `rect_at_point()`。

- Cursor image
  - Windows 目前 best-effort 轉 RGBA。
  - macOS 需要回傳 `(image, hotspot_x, hotspot_y, screen_x, screen_y)` 等同資料。

- Permissions
  - Windows 目前沒有集中 permission flow。
  - macOS 應在啟動或首次使用時檢查 Screen Recording/Accessibility，並提示使用者。

## macOS Implementation Layout

- `platforms/macos.py`: 權限、Core Graphics/Accessibility 視窗查詢、游標與全域快捷鍵。
- `capture.py`: 保留跨平台擷取流程，僅在平台能力入口委派給 macOS backend。
- `app.py`: Windows native filter、macOS event tap 與其他平台 fallback 的生命週期管理。

## Manual Acceptance Checklist

每個平台至少要手動驗收：

- 快捷鍵可觸發，且不把按鍵送給焦點 app。
- 無延遲和有延遲流程都符合：先決定目標，倒數後截即時畫面。
- 全螢幕、矩形、焦點視窗、選取視窗/控制項都可用。
- Chrome 等具有 transient popup 的應用程式，焦點視窗擷取不會誤截連結網址或 tooltip。
- ESC 可取消矩形/視窗選取。
- 包含游標時顯示當下真實游標。
- 截圖後影像出現在編輯區左上角。
- 複製到剪貼簿可貼到常見 app。
- 存檔 PNG/JPG 正常。
- 最小化隱藏、系統匣雙擊顯示、右鍵退出正常。
