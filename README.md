# FastShot

FastShot 是以 Python 實作的桌面截圖工具，主打全域快捷鍵、系統匣常駐、多頁籤編輯與快速複製/存檔。現階段 Windows 功能已接近完整；macOS 跨平台支援尚未完成，後續實作前請先閱讀 [Cross-Platform Notes](docs/cross-platform.md)。

## Current Status

- Windows: 主要功能已實作並經手動測試調整。
- macOS: 尚未完成平台層實作，尤其是全域快捷鍵、視窗/控制項選取、真實游標擷取與剪貼簿細節。
- Linux: 僅保留基本架構與部分通用能力，尚未作為主要目標平台。

## Quick Start

```powershell
uv sync
uv run fastshot
```

程式啟動後會隱藏主視窗並留在系統匣。雙擊系統匣圖示可顯示編輯視窗，右鍵選單可退出。

## Windows Shortcuts

- `Alt+Shift+A`: 擷取目前焦點視窗
- `Alt+Shift+R`: 擷取矩形區域
- `Alt+Shift+F`: 擷取全螢幕
- `Alt+Shift+W`: 選取視窗或控制項後擷取

編輯工具快捷鍵：

- `Alt+P`: 自由畫筆
- `Alt+L`: 線條
- `Alt+A`: 箭頭
- `Alt+R`: 矩形
- `Alt+T`: 文字
- `Alt+M`: 馬賽克
- `Alt+C`: 線條粗細與顏色
- `Ctrl++` / `Ctrl+=`: 放大
- `Ctrl+-`: 縮小
- `Ctrl+0`: 重設縮放

## Project Docs

- [PRD](PRD.md): 原始產品需求。
- [Architecture](docs/architecture.md): 專案結構、主要模組與資料流。
- [Cross-Platform Notes](docs/cross-platform.md): Windows/macOS/Linux 差異與 macOS 後續實作重點。

## Development

```powershell
uv sync
uv run pytest -q
.\.venv\Scripts\python.exe -m compileall src tests
```

若 FastShot 正在執行，`compileall` 有時會因 `__pycache__` 或 executable 被鎖而失敗；先關閉或停止 `fastshot.exe` 後再重跑。
