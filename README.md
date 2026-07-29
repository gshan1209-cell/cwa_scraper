# CWA 氣象開放資料下載器 (F-A0010-001)

此專案提供 Python 命令列工具，用於自交通部中央氣象署（CWA）氣象資料開放平臺下載天氣預報資料集，預設為 **F-A0010-001｜一週農業氣象預報**。

本 Repository 的正式定位是 **L4 共用氣象資料 Adapter**。它負責下載與保存 CWA 回應，不是官方氣象 Canonical Owner，也不自行產生氣象資料或農事決策。

## 安全基線

- TLS 憑證驗證永遠啟用。
- SSL 驗證失敗時直接停止，禁止改用 `verify=False` 重試。
- API Key 優先使用 `CWA_API_KEY` 環境變數。
- `--api-key`／`-k` 只為相容舊用法保留，使用時會顯示安全警告；真實金鑰可能出現在 Shell History 或 Process List，不建議使用。
- 互動式輸入使用隱藏輸入，不回顯金鑰。
- API Key 不得寫入 Git、Log、Agent Context 或 Evidence。
- JSON 解析失敗不會保存原始內容並誤報成功。

目前 Production Status 維持 `blocked-pending-independent-verification`，需由 Codex 完成獨立 Test-only PR 後才能重新評估。

## 前提條件

1. 註冊 CWA 氣象資料開放平臺會員並取得 API 授權碼。
2. 安裝 Python 3.8 以上版本。
3. 安裝依賴：

```bash
pip install -r requirements.txt
```

## API Key 設定

### 環境變數（推薦）

將 `.env.example` 複製為 `.env`，或在執行環境設定：

```env
CWA_API_KEY=您的授權碼
```

直接執行：

```bash
python cwa_scraper.py
```

### 安全互動式輸入

未設定 `CWA_API_KEY` 且目前是互動式終端機時，程式會以隱藏輸入要求 API Key。

### 舊版命令列參數（不建議）

```bash
python cwa_scraper.py --api-key 您的授權碼
```

此方式僅保留相容性，會顯示安全警告。請勿在正式環境使用真實金鑰。

## 使用方式

下載預設 JSON 資料集：

```bash
python cwa_scraper.py
```

下載 XML：

```bash
python cwa_scraper.py --format XML
```

指定輸出目錄：

```bash
python cwa_scraper.py --out-dir custom_folder
```

指定其他資料集：

```bash
python cwa_scraper.py --dataset F-C0032-001
```

完整說明：

```bash
python cwa_scraper.py --help
```

## 輸出

成功下載後，檔案名稱包含 Dataset ID 與本機下載時間：

```text
downloads/F-A0010-001_YYYYMMDD_HHMMSS.json
downloads/F-A0010-001_YYYYMMDD_HHMMSS.xml
```

下載檔案是 CWA 回應的 Runtime Evidence／Cache，不得描述為本系統自行發布的官方資料。

## Fail-Closed 錯誤狀態

| Exit Code | 狀態 |
|---:|---|
| `0` | 成功 |
| `2` | API Key 缺失或設定錯誤 |
| `3` | TLS 憑證驗證失敗 |
| `4` | Timeout、連線或其他網路失敗 |
| `5` | 401、404、其他 HTTP 或 CWA API 錯誤 |
| `6` | JSON 解析失敗 |
| `7` | 輸出目錄或檔案寫入失敗 |

任何失敗都不得被轉換成空資料或成功訊息。

## 驗證分工

Implementation PR 完成後，Codex 需在獨立 Test-only PR 提供：

```bash
python -m py_compile cwa_scraper.py
python cwa_scraper.py --help
```

並驗證：

- API Key 缺失。
- CLI Key 警告且不洩漏 Secret。
- 401、404、Timeout、Connection Error。
- SSL 驗證失敗時不呼叫第二次 Request，也不使用 `verify=False`。
- Invalid JSON 不寫檔、不回報成功。
- File Write Failure。
- 受控環境中的去敏 Live CWA Download。

未執行的項目維持 `not-run`，不得提前宣稱 Verified Conformance。
