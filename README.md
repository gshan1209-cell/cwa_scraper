# CWA 氣象開放資料下載器 (F-A0010-001)

此專案提供了一個 Python 命令列工具，用於自交通部中央氣象署 (CWA) 氣象資料開放平臺下載天氣預報資料集，特別是針對 **F-A0010-001 (一週農業氣象預報)** 資料集。

## 前提條件

1.  **註冊氣象開放資料會員**：
    *   造訪 [中央氣象署氣象資料開放平臺](https://opendata.cwa.gov.tw/)。
    *   註冊並登入會員。
    *   前往「會員專區」 -> 「API 授權碼」，取得您的專屬授權碼 (API Key，通常格式為 `CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)。

2.  **安裝 Python 依賴套件**：
    *   確認您的系統已安裝 Python 3.8+。
    *   使用 pip 安裝所需套件：
        ```bash
        pip install -r requirements.txt
        ```

## 配置方式

您可以透過以下三種方式配置 API 授權碼：

1.  **環境變數檔案 (推薦)**：
    將 `.env.example` 複製並重新命名為 `.env`，然後填入您的 API Key：
    ```env
    CWA_API_KEY=您的授權碼(CWA-xxxxxxxx-...)
    ```

2.  **命令列參數**：
    在執行程式時直接透過 `-k` 或 `--api-key` 參數傳入：
    ```bash
    python cwa_scraper.py -k 您的授權碼
    ```

3.  **互動式輸入**：
    如果程式未在環境變數或命令列中找到 API Key，且您正在互動式終端機中運行，程式將會主動提示您輸入。

## 使用說明

直接運行腳本，即可下載預設資料集 (`F-A0010-001`) 的 `JSON` 格式檔案：

```bash
python cwa_scraper.py
```

### 命令列參數選項

```text
usage: cwa_scraper.py [-h] [-k API_KEY] [-d DATASET] [-f {JSON,XML}] [-o OUT_DIR] [--no-pretty]

Download forecast dataset files from the Taiwan Central Weather Administration (CWA).

options:
  -h, --help            顯示此說明訊息並結束
  -k API_KEY, --api-key API_KEY
                        CWA API 授權碼。亦可在 .env 檔案中設定 CWA_API_KEY。
  -d DATASET, --dataset DATASET
                        資料集代碼 (預設: F-A0010-001)。
  -f {JSON,XML}, --format {JSON,XML}
                        輸出資料格式 (預設: JSON)。
  -o OUT_DIR, --out-dir OUT_DIR
                        存檔目錄路徑 (預設: downloads)。
  --no-pretty           停用 JSON 格式化輸出。
```

### 使用範例

*   **下載 XML 格式檔案**：
    ```bash
    python cwa_scraper.py -f XML
    ```

*   **指定不同的輸出目錄**：
    ```bash
    python cwa_scraper.py -o custom_folder
    ```

*   **下載其他氣象資料集 (例如 F-C0032-001 - 今明 36 小時天氣預報)**：
    ```bash
    python cwa_scraper.py -d F-C0032-001
    ```

## 檔案輸出說明

下載的檔案將以包含時間戳記的檔名存檔於指定目錄中：
*   `downloads/F-A0010-001_YYYYMMDD_HHMMSS.json`
*   `downloads/F-A0010-001_YYYYMMDD_HHMMSS.xml`
