# Cross-Platform Notes

FastShot 的 UI 大部分使用 PySide6，可跨平台重用；但截圖、全域快捷鍵、游標、視窗選取與剪貼簿都是平台相依區域。macOS 實作時請優先處理本文件列出的邊界。

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

macOS 尚未完成。PRD 中「macOS 把 alt 換成 opt」只是產品需求，不代表平台層已實作。

macOS 待實作重點：

- 全域快捷鍵：需要能攔截並 consume `Option+Shift+...`，避免傳給焦點 app。
- 螢幕錄製權限：截圖需要 Screen Recording permission。
- Accessibility 權限：焦點視窗、視窗/控制項選取、真實游標與部分快捷鍵行為可能需要 Accessibility permission。
- 視窗 bounds：需要對應 Windows DWM bounds 的 macOS window bounds 實作。
- 控制項 hit-test：Windows UI Automation 需替換成 macOS Accessibility API。
- 真實游標：需要從 macOS cursor API 取得當下 cursor image 與 hotspot。
- 剪貼簿：確認 `QClipboard` 寫入影像在 macOS 目標 app 中可正常貼上。

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

## Suggested macOS Implementation Order

1. 保留現有 Qt UI，不改 `main_window.py` 與 `canvas.py`，先只替換平台層。
2. 新增平台 backend 介面，先讓 Windows 現有邏輯搬入 Windows backend。
3. 實作 macOS 全螢幕與矩形截圖。
4. 實作 macOS 全域快捷鍵並確認事件不送到焦點 app。
5. 實作焦點視窗 bounds。
6. 實作視窗/控制項選取與 hover 框線。
7. 實作真實游標貼圖。
8. 補 macOS 手動驗收清單與必要 smoke tests。

## Manual Acceptance Checklist

每個平台至少要手動驗收：

- 快捷鍵可觸發，且不把按鍵送給焦點 app。
- 無延遲和有延遲流程都符合：先決定目標，倒數後截即時畫面。
- 全螢幕、矩形、焦點視窗、選取視窗/控制項都可用。
- ESC 可取消矩形/視窗選取。
- 包含游標時顯示當下真實游標。
- 截圖後影像出現在編輯區左上角。
- 複製到剪貼簿可貼到常見 app。
- 存檔 PNG/JPG 正常。
- 最小化隱藏、系統匣雙擊顯示、右鍵退出正常。
