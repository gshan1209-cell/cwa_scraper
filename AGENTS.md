# CWA Scraper｜Agent Entry

## 1. 啟動順序

執行任何開發、除錯或驗證前，依序閱讀：

1. `README.md`
2. `.ai-company/repo-manifest.yaml`
3. `.ai-company/dual-interface.yaml`
4. `.ai-company/agent-context.yaml`
5. `cwa_scraper.py`
6. `requirements.txt`

## 2. 系統定位

本 Repository 是中央氣象署開放資料的下載 Adapter，不是氣象預報 Canonical Owner，也不是農事決策平台。

預設資料集：

```text
F-A0010-001｜一週農業氣象預報
```

輸出 JSON／XML 檔案只是從 CWA 下載的 Runtime Evidence／Cache，不得被描述為自行產生的官方資料。

## 3. 狀態誠信

- 沒有實際呼叫 CWA API 時，狀態維持 `not-run`。
- API Key 缺失、401、404、Timeout、JSON 解析失敗與檔案寫入失敗必須明確回報。
- 不得將下載失敗表示為空資料或成功。
- 輸出資料必須保留 Dataset ID、下載時間與來源。
- 本次加入雙入口，不代表下載器 Runtime、SSL、Schema 或資料正確性已驗證。

## 4. 安全規則

- `CWA_API_KEY` 只可存在環境變數或互動式輸入，不得提交到 Git、Log、Context 或 Evidence。
- 不建議在命令列直接傳入真實 API Key，因為可能出現在 Process List 或 Shell History。
- 目前程式在 SSL 驗證失敗時會自動以 `verify=False` 重試；此為已知安全風險，不得描述為安全的正式環境行為。
- 不得自動變更正式資料來源、Dataset ID、Credential 或 TLS Policy。
- 不得自動 Merge、Release 或執行排程部署。

## 5. 修改與驗證

修改前先確認任務是否只涉及：

- CLI Argument。
- CWA API Request。
- Response Parsing。
- Output File。
- Preview Display。
- Security／TLS。
- Documentation／Governance。

基本驗證至少記錄：

```bash
python -m py_compile cwa_scraper.py
python cwa_scraper.py --help
```

需要真實 CWA API Key 的 Live Test 必須在受控環境執行，Evidence 不得包含 Secret。

## 6. 人工核准邊界

以下操作需人工核准：

- 正式 Credential 或 Secret 變更。
- 關閉 TLS 驗證作為正式預設。
- 正式資料集或資料來源切換。
- 排程、發布、部署或下游 Canonical Import。
