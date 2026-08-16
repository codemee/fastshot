# FShot

[繁體中文](https://github.com/codemee/fshot/blob/main/README.md) | [English](https://github.com/codemee/fshot/blob/main/README.en.md)

FShot 是以 Python 實作的桌面截圖工具，主打全域快捷鍵、系統匣常駐、多頁籤編輯與快速複製/存檔。目前支援 Windows 與 macOS；平台權限與驗收方式請閱讀 [Cross-Platform Notes](https://github.com/codemee/fshot/blob/main/docs/cross-platform.md)。

## Current Status

- Windows: 主要功能已實作並經手動測試調整。
- macOS: 已實作 Quartz 全域快捷鍵、螢幕擷取、焦點視窗、視窗/控制項選取與游標擷取。
- Linux: 僅保留基本架構與部分通用能力，尚未作為主要目標平台。

## Quick Start

FShot 可從 [PyPI](https://pypi.org/project/fshot/) 安裝。不需安裝即可使用 `uvx` 執行最新正式版本：

```powershell
uvx fshot
```

第一次執行會從 PyPI 下載套件並建立 uv 快取環境，後續會重用快取。臨時試用建議使用 `uvx`，若要長期使用則安裝為 uv tool。

使用 uv 從 PyPI 安裝：

```powershell
uv tool install fshot
fshot
```

安裝後可直接執行 `fshot`；更新至 PyPI 最新版本：

```powershell
uv tool upgrade fshot
```

使用 `uv tool install` 安裝時，FShot 啟動後會在背景每日檢查一次 PyPI。系統匣選單可手動「檢查更新…」或停用自動檢查；發現新版時可選擇更新並重新啟動、稍後處理或略過該版本。更新前若有尚未儲存的截圖，FShot 會先要求確認。`uvx`、原始碼開發環境與其他非 uv tool 安裝方式只會提供手動更新指引，不會自行修改環境。

若要直接從 GitHub 測試 `main` 的最新開發成果：

```powershell
uv tool install --force "fshot @ git+https://github.com/codemee/fshot.git@main"
```

從原始碼啟動開發環境：

```powershell
uv sync
uv run fshot
```

程式啟動後會隱藏主視窗並留在系統匣。雙擊系統匣圖示可顯示編輯視窗，右鍵選單可退出。
工具列的主題按鈕可單擊循環切換「跟隨系統 → 淺色 → 深色」；預設跟隨作業系統配色，選擇會保留至下次啟動。太陽代表淺色、月亮代表深色，分隔排列的太陽與月亮代表跟隨系統。
語言按鈕可單擊循環切換「跟隨系統 → 繁體中文 → English」，並保留使用者選擇；圖示分別為 `文/A`、`中` 與 `En`。
工具列按鈕的提示文字會依目前語言顯示，具備快捷鍵的動作也會在提示中列出對應按鍵。
畫線與箭頭共用同一個畫線工具。畫線按鈕旁的下拉面板可分別將線條起點與終點設為無箭頭、箭頭或實心圓，兩端樣式可任意組合。
工具列的鍵盤圖示可設定四種截圖方式及「重複前一次擷取」的全域快捷鍵。每組可選 Ctrl、Shift、Alt 與 A–Z 字母；Shift 必須搭配 Ctrl 或 Alt。「使用預設」會將面板中的五組欄位恢復為預設值；按 OK 且系統註冊成功後才會套用並保留設定，Cancel 不會變更目前快捷鍵。

圖片也可透過拖放或剪貼簿加入編輯器：拖放圖片會以完整檔名建立頁籤、保留來源路徑並在修改後寫回原檔；直接貼上影像或從檔案管理器複製圖片後貼上，會以截圖時間格式建立新的未存檔頁籤。成功存檔後會記住檔案所在資料夾，其他尚未存檔的頁籤會從該資料夾開啟儲存交談窗。Windows/Linux 使用 `Ctrl+V`，macOS 使用 `Command+V`。

## Windows Shortcuts

- `Ctrl+Shift+Q`: 重複前一次的截圖方式（矩形區域與選取的視窗／控制項會沿用前次目標，可在設定面板自訂）
- `Ctrl+Shift+A`: 擷取目前焦點視窗
- `Ctrl+Shift+R`: 擷取矩形區域
- `Ctrl+Shift+F`: 擷取全螢幕
- `Ctrl+Shift+W`: 選取視窗或控制項後擷取

macOS 使用相同的 `Ctrl+Shift` 字母組合。首次執行時，請依系統提示授予「螢幕錄製」與「輔助使用」權限。目前 FShot 是透過 `uv`／`uvx` 執行，而非封裝成獨立的 macOS App，因此系統設定中的授權對象通常是啟動指令所在的 App，例如「終端機」、iTerm2 或 IDE。授權後請完全結束並重新開啟該 App，再重新執行 FShot。

編輯工具快捷鍵：

- `Alt+P`: 自由畫筆
- `Alt+L`: 線條
- `Alt+R`: 矩形
- `Alt+T`: 文字
- `Alt+M`: 馬賽克
- `Alt+C`: 線條粗細與顏色
- `Ctrl++` / `Ctrl+=`: 放大
- `Ctrl+-`: 縮小
- `Ctrl+0`: 重設縮放
- `F2`: 直接在目前標籤頁重新命名已存檔的檔案（macOS 使用 `Return`）

已存檔的標籤頁也可直接雙擊名稱進入重新命名；副檔名會保留不變。

## Project Docs

- [PRD](https://github.com/codemee/fshot/blob/main/PRD.md): 原始產品需求。
- [Architecture](https://github.com/codemee/fshot/blob/main/docs/architecture.md): 專案結構、主要模組與資料流。
- [Cross-Platform Notes](https://github.com/codemee/fshot/blob/main/docs/cross-platform.md): Windows/macOS/Linux 差異與 macOS 後續實作重點。

## Development

```shell
uv sync
uv run pytest -q
uv run python -m compileall src tests
```

若 FShot 正在執行，`compileall` 有時會因 `__pycache__` 或 executable 被鎖而失敗；先關閉或停止 `fshot.exe` 後再重跑。
