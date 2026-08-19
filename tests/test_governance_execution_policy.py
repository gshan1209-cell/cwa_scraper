from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SURFACES = [
    ROOT / "AGENTS.md",
    ROOT / ".ai-company" / "repo-manifest.yaml",
    ROOT / ".ai-company" / "agent-context.yaml",
    ROOT / ".ai-company" / "status-snapshot.yaml",
    ROOT / ".ai-company" / "dual-interface.yaml",
]

CURRENT_CHAIN = [
    "DS-003@2.1.1",
    "RESP-DEV-AGENT-001@2.1.1",
    "PROC-VALIDATION-TASK-001@2.1.1",
    "PROC-CODEX-POST-MAIN-VALIDATION-001@1.1.1",
    "PROC-CHATGPT-AUDIT-001@2.1.1",
    "PROC-ISSUE-CLOSURE-001@2.1.1",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_active_surfaces_do_not_publish_test_only_execution() -> None:
    joined = "\n".join(read(path) for path in SURFACES)
    assert "Codex Test-only PR" not in joined
    assert "test-only PR" not in joined
    assert "independent-test-only-validation" not in joined
    assert "create a test-only PR" not in joined


def test_current_post_main_validation_handoff_is_projected() -> None:
    agents = read(ROOT / "AGENTS.md")
    for ref in CURRENT_CHAIN:
        assert ref in agents

    joined = "\n".join(read(path) for path in SURFACES[1:])
    assert "DS-003@2.1.1" in joined
    assert "testPullRequest: null" in joined
    assert "validatorRepositoryWrite: false" in joined
    assert "pendingValidationFreezesMain: false" in joined
    assert "AI-Workstream#242" in joined


def test_status_no_longer_claims_pending_merge() -> None:
    status = read(ROOT / ".ai-company" / "status-snapshot.yaml")
    assert "complete-pending-merge" not in status
    assert "implementation: merged-validation-pending" in status
    assert "productionStatus: blocked-pending-independent-live-evidence" in status
    assert "liveCwaDownload: not-run-blocked-pending-api-key" in status


def test_tls_and_secret_safety_remain_fail_closed() -> None:
    joined = "\n".join(read(path) for path in SURFACES)
    assert "tlsVerificationRequired: true" in joined
    assert "tlsVerificationBypass: forbidden" in joined
    assert "sslFailurePolicy: fail-closed" in joined
    assert "apiKeyInContextOrEvidence: forbidden" in joined
    assert "verifiedConformance: false" in joined
