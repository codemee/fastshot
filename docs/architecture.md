# Architecture

本文是給初次接觸 FastShot 專案的導覽。若要做 macOS 跨平台實作，請同時閱讀 [cross-platform.md](cross-platform.md)。

## Entry Points

- `pyproject.toml`: 專案 metadata、依賴與 `fastshot` command。
- `src/fastshot/__main__.py`: `python -m fastshot` 入口。
- `src/fastshot/app.py`: Qt application、系統匣、全域快捷鍵與截圖流程 orchestration。

## Main Modules

- `app.py`
  - 建立 `QApplication`、`FastShotApplication`、系統匣圖示。
  - Windows 使用 `RegisterHotKey` 接收全域快捷鍵，避免快捷鍵送到焦點視窗。
  - 收到快捷鍵後隱藏編輯視窗，呼叫 `CaptureService`，截圖完成後加入編輯頁籤並複製到剪貼簿。

- `capture.py`
  - 管理所有截圖模式：全螢幕、矩形區域、焦點視窗、選取視窗/控制項。
  - Windows 特有能力集中於此：DWM frame bounds、UI Automation 控制項 hit-test、真實游標 bitmap、`mss`/`ImageGrab` fallback。
  - 延遲截圖流程也在此：先決定目標矩形，再顯示倒數 overlay，最後擷取即時畫面。

- `main_window.py`
  - 編輯主視窗、toolbar、多頁籤、存檔/另存、縮放、設定面板。
  - 每個截圖頁籤持有一個 `ImageCanvas`。

- `canvas.py`
  - 編輯區與影像操作。
  - 支援自由畫筆、線條、箭頭、矩形、文字、馬賽克、裁切控制方塊、縮放與 undo。
  - Canvas 會在圖片外圍預留 padding，讓裁切控制方塊不覆蓋圖片內容。

- `document.py`
  - `ShotDocument` 管理頁籤標題、存檔路徑、dirty/unsaved 狀態。

- `icons.py`
  - 程式內自繪 toolbar/system tray icon。

- `settings.py`
  - `CaptureMode`、`Tool`、`CaptureSettings`、`DrawingSettings`。

- `qt_image.py`
  - Pillow 與 Qt image/pixmap 轉換 helper。

## Capture Flow

1. `app.py` 收到全域快捷鍵。
2. 編輯視窗先隱藏，避免被截入畫面。
3. `CaptureService._rect_for_mode()` 決定擷取矩形。
4. 若有延遲，顯示右下角倒數 overlay；使用者可繼續操作電腦。
5. 倒數結束後隱藏 overlay，呼叫 `_grab_rect()` 擷取即時畫面。
6. 若啟用包含游標，best-effort 貼上當下真實游標。
7. `EditorWindow.add_shot()` 建立新頁籤並顯示於左上角。
8. `EditorWindow.copy_current()` 複製目前影像到剪貼簿。

## Editing Model

目前編輯是直接修改 `QImage`，每次操作前把當前影像複製進 undo stack。這讓實作簡單，但不是向量化/物件化模型；未來若要支援重新選取已畫物件、調整文字內容或匯出可編輯圖層，需要重構 canvas model。

裁切也是影像操作：拖曳圖片外圍控制方塊後，滑鼠放開即裁切並進入 undo stack。

## Testing

目前測試以輕量單元測試和 Qt offscreen smoke 為主：

- `tests/test_document.py`: tab title、dirty/save 狀態、文件 reindex。
- 手動 smoke 常用 `.venv\Scripts\python.exe`，避免 `uv` cache 權限或執行中 executable lock 影響檢查。

重要的 GUI/OS 行為仍需手動驗收，尤其是全域快捷鍵、視窗選取、游標擷取與剪貼簿。
