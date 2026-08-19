# CWA Scraper｜Agent Entry

## 1. 啟動順序

執行任何開發、除錯或驗證前，依序閱讀：

1. `README.md`
2. `.ai-company/repo-manifest.yaml`
3. `.ai-company/status-snapshot.yaml`
4. `.ai-company/dual-interface.yaml`
5. `.ai-company/agent-context.yaml`
6. `cwa_scraper.py`
7. `requirements.txt`
8. 與當前任務對應的 Issue、PR 與 Evidence

## 2. 系統定位

本 Repository 是中央氣象署開放資料的 **L4 共用氣象資料 Adapter**。

```yaml
systemType: shared-weather-data-adapter
owner: cwa_scraper
parentSystem: AI-Workstream
consumers:
  - smartbuy-ai
  - scrape_weather
```

它不是氣象預報 Canonical Owner，也不是農事決策平台。輸出 JSON／XML 只是從 CWA 下載的 Runtime Evidence／Cache，不得被描述為自行產生的官方資料。

## 3. Minimum Evidence Contract

此 Managed Repository 必須保留：

```text
README.md
AGENTS.md
.ai-company/repo-manifest.yaml
.ai-company/agent-context.yaml
.ai-company/status-snapshot.yaml
```

Local Entry 存在不等於 Verified Conformance。

Evidence 必須記錄：

```yaml
observedSourceSha: <exact commit inspected>
observedBranch: main
reviewedAt: <RFC3339 with timezone>
reviewer: <identity>
evidenceRefs: []
verificationStatus: not-run|partial|passed|failed|blocked
```

## 4. 狀態誠信

- 沒有實際呼叫 CWA API 時，Live Status 維持 `not-run`。
- API Key 缺失、401、404、Timeout、Connection Error、TLS Failure、Invalid JSON 與 File Write Failure 必須明確區分。
- 不得將下載失敗表示為空資料或成功。
- Invalid JSON 不得保存原始內容後繼續宣稱完成。
- 輸出必須保留 Dataset ID 與下載時間；來源固定為 CWA File API。
- README、Manifest、Context 或程式碼存在，不代表 Runtime、TLS、Schema 或資料正確性已驗證。
- Historical PR #4 的 20/20 security/mock Evidence 保留作 provenance；current validation 必須由 AI-Workstream #242 綁定 execution-time latest Main。

## 5. 強制安全規則

- TLS 憑證驗證永遠啟用。
- 捕捉 `SSLError` 後必須 Fail Closed，禁止再次呼叫 `requests.get(..., verify=False)`。
- 不得停用或忽略 `InsecureRequestWarning` 以掩蓋 TLS 問題。
- `CWA_API_KEY` 優先由環境變數提供。
- 互動式輸入必須使用隱藏輸入。
- `--api-key`／`-k` 僅為向後相容保留，使用時必須警告 Shell History／Process List 風險。
- API Key 不得提交到 Git、Log、Context、Snapshot、Test Fixture 或 Evidence。
- 不得自動修改正式資料來源、Dataset ID、Credential、TLS Policy、排程、Release 或 Deployment。

## 6. Development / Validation Boundary

一個 Implementation Scope 使用一個 Branch 與一個正常 Repository-local PR。Primary Development Agent 負責實作、remediation 與可用的 Sandbox-first/focused validation；PR 自身 Merge Gate滿足後可合併 Main，Pending Supplemental Validation 不凍結 Main。

需要受控 Live API、完整環境或獨立安全驗證時，使用 AI-Workstream Post-Main Validation Task；目前 TLS/live handoff 是 `AI-Workstream#242`。Qualified independent validator 只讀 execution-time latest Main、記錄 exact `testedMainSha`、回傳 Evidence／Findings，不建立 test-only PR。

Current exact authority：

```yaml
policy: DS-003@2.1.1
responsibility: RESP-DEV-AGENT-001@2.1.1
validationTaskProcedure: PROC-VALIDATION-TASK-001@2.1.1
codexProcedure: PROC-CODEX-POST-MAIN-VALIDATION-001@1.1.1
chatgptAuditProcedure: PROC-CHATGPT-AUDIT-001@2.1.1
issueClosureProcedure: PROC-ISSUE-CLOSURE-001@2.1.1
currentValidationTask: AI-Workstream#242
testPullRequest: null
validatorRepositoryWrite: false
validatorRemediation: false
validatorBranchCreation: false
validatorPullRequestCreation: false
validatorMerge: false
validatorSourceIssueClosure: false
pendingValidationFreezesMain: false
```

Known GitHub Actions account-level quota／billing／spending-limit pre-execution blocker 使用 `WAIVED_BY_OWNER / NOT_RUN`，不得主動 rerun 只為重現相同 blocker，也不得表示為 PASS。

## 7. 驗證要求

Current read-only validation至少涵蓋：

```bash
python -m py_compile cwa_scraper.py test_codex_verification.py
python cwa_scraper.py --help
python -m unittest test_codex_verification -v
```

並確認：

1. Missing Key → Exit Code `2`。
2. CLI Key 會警告，但不得輸出 Key 本身。
3. SSL Failure → Exit Code `3`，只能呼叫一次 Request、沒有 `verify=False`。
4. Timeout／Connection Error → Exit Code `4`。
5. 401／404／HTTP Error → Exit Code `5`。
6. Invalid JSON → Exit Code `6` 且不建立輸出檔。
7. File Write Failure → Exit Code `7`。
8. JSON／XML 成功案例。
9. Environment Key 優先；互動式輸入使用 `getpass`，不得回顯 Secret。

受控 Live CWA Download 僅在 authorized `CWA_API_KEY` 已存在於受控環境時執行；沒有 Key 時維持 `blocked/not-run`，不得要求、輸出或保存 Credential，也不得將 Mock Evidence當 Live PASS。

## 8. 人工核准邊界

以下操作仍需人工核准：

- 正式 Credential 或 Secret 變更。
- TLS Policy 變更。
- 正式 Dataset 或資料來源切換。
- 下游 Canonical Import。
- 排程、發布、部署或 Production Unblock。
