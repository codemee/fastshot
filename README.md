# FastShot

FastShot 是以 Python 實作的桌面截圖工具，主打全域快捷鍵、系統匣常駐、多頁籤編輯與快速複製/存檔。目前支援 Windows 與 macOS；平台權限與驗收方式請閱讀 [Cross-Platform Notes](docs/cross-platform.md)。

## Current Status

- Windows: 主要功能已實作並經手動測試調整。
- macOS: 已實作 Quartz 全域快捷鍵、螢幕擷取、焦點視窗、視窗/控制項選取與游標擷取。
- Linux: 僅保留基本架構與部分通用能力，尚未作為主要目標平台。

## Quick Start

```powershell
uv sync
uv run fastshot
```

程式啟動後會隱藏主視窗並留在系統匣。雙擊系統匣圖示可顯示編輯視窗，右鍵選單可退出。
工具列的主題按鈕可單擊循環切換「跟隨系統 → 淺色 → 深色」；預設跟隨作業系統配色，選擇會保留至下次啟動。太陽代表淺色、月亮代表深色，分隔排列的太陽與月亮代表跟隨系統。
語言按鈕可單擊循環切換「跟隨系統 → 繁體中文 → English」，並保留使用者選擇；圖示分別為 `文/A`、`中` 與 `En`。
工具列按鈕的提示文字會依目前語言顯示，具備快捷鍵的動作也會在提示中列出對應按鍵。

圖片也可透過拖放或剪貼簿加入編輯器：拖放圖片會以完整檔名建立頁籤、保留來源路徑並在修改後寫回原檔；直接貼上影像或從檔案管理器複製圖片後貼上，會以截圖時間格式建立新的未存檔頁籤。Windows/Linux 使用 `Ctrl+V`，macOS 使用 `Command+V`。

## Windows Shortcuts

- `Alt+Shift+A`: 擷取目前焦點視窗
- `Alt+Shift+R`: 擷取矩形區域
- `Alt+Shift+F`: 擷取全螢幕
- `Alt+Shift+W`: 選取視窗或控制項後擷取

macOS 使用相同字母組合，將 `Alt` 改為 `Option`。首次執行時，請依系統提示授予「螢幕錄製」與「輔助使用」權限；授權後可能需要重新啟動 FastShot。

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

```shell
uv sync
uv run pytest -q
uv run python -m compileall src tests
```

若 FastShot 正在執行，`compileall` 有時會因 `__pycache__` 或 executable 被鎖而失敗；先關閉或停止 `fastshot.exe` 後再重跑。
