#!/usr/bin/env python3
"""
Codex Test-only Verification Suite
Repository: gshan1209-cell/cwa_scraper
Issue: #3 – test-only: Codex 驗證 TLS Fail Closed 與 CWA Failure States
Base SHA: 84884e915d24b93aff185b9a5ff37d030e44470d

All tests use Mock/Monkeypatch. No live CWA API calls are made.
Live CWA download status: not-run (blocked-pending-api-key)
"""

import ast
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure the module under test is importable
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import cwa_scraper as cwa

_DUMMY_KEY = "CWA-DUMMY-TEST-KEY-12345"
_DUMMY_ENV = {"CWA_API_KEY": _DUMMY_KEY}


# ─────────────────────────────────────────────────────────────────────────────
# Security AST checks – parse source as AST to find actual code (not comments)
# ─────────────────────────────────────────────────────────────────────────────
class TestSecurityStaticAnalysis(unittest.TestCase):
    """Verify via AST that verify=False is never used as executable code."""

    @classmethod
    def setUpClass(cls):
        src = (pathlib.Path(__file__).parent / "cwa_scraper.py").read_text(encoding="utf-8")
        cls.source_text = src
        cls.tree = ast.parse(src)

    def test_verify_false_not_in_executable_ast(self):
        """verify=False must not appear as an AST keyword argument."""
        violations = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "verify" and isinstance(kw.value, ast.Constant):
                        if kw.value.value is False:
                            violations.append(f"Line {node.lineno}")
        self.assertEqual(
            violations, [],
            f"SECURITY VIOLATION: verify=False used in AST at: {violations}",
        )

    def test_insecure_request_warning_not_suppressed(self):
        """urllib3.disable_warnings and InsecureRequestWarning must be absent."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                # Check for urllib3.disable_warnings(...)
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "disable_warnings":
                        self.fail(f"urllib3.disable_warnings found at line {node.lineno}")
            if isinstance(node, ast.Name):
                if node.id == "InsecureRequestWarning":
                    self.fail(f"InsecureRequestWarning reference found at line {node.lineno}")

    def test_exit_codes_defined_correctly(self):
        """All required exit codes must be defined."""
        self.assertEqual(cwa.EXIT_OK, 0)
        self.assertEqual(cwa.EXIT_CONFIG, 2)
        self.assertEqual(cwa.EXIT_TLS, 3)
        self.assertEqual(cwa.EXIT_NETWORK, 4)
        self.assertEqual(cwa.EXIT_HTTP, 5)
        self.assertEqual(cwa.EXIT_PARSE, 6)
        self.assertEqual(cwa.EXIT_WRITE, 7)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Missing API Key → EXIT_CONFIG (2)
# ─────────────────────────────────────────────────────────────────────────────
class TestMissingApiKey(unittest.TestCase):

    def test_missing_key_exits_config(self):
        """No env key, no CLI key, no tty → EXIT_CONFIG (2)."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("cwa_scraper.os.getenv", return_value=None),
            patch("cwa_scraper.sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = False
            result = cwa.main([])
        self.assertEqual(result, cwa.EXIT_CONFIG)


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: --api-key warning; key value NOT in stderr
# ─────────────────────────────────────────────────────────────────────────────
class TestCliKeyWarning(unittest.TestCase):

    def test_cli_key_warning_key_not_in_stderr(self):
        """--api-key must emit warning; the key value must NOT appear in stderr."""
        test_key = "CWA-SECRET-MUST-NOT-APPEAR-IN-STDERR"
        args = cwa.parse_arguments(["-k", test_key])
        captured_stderr = io.StringIO()

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("cwa_scraper.os.getenv", return_value=None),
            patch("sys.stderr", captured_stderr),
        ):
            result = cwa.resolve_api_key(args)

        self.assertEqual(result, test_key)
        stderr_text = captured_stderr.getvalue()
        self.assertIn("warning", stderr_text.lower(), "Warning must be in stderr")
        self.assertNotIn(test_key, stderr_text, "Key value must NOT appear in stderr")


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: SSLError → EXIT_TLS (3); exactly 1 request; no verify=False in call
# ─────────────────────────────────────────────────────────────────────────────
class TestSSLFailure(unittest.TestCase):

    def test_ssl_error_exits_tls_single_call_no_verify_false(self):
        """SSLError: EXIT_TLS; exactly 1 requests.get call; verify=False not used."""
        import requests as req

        call_log = []

        def tracking_get(*args, **kwargs):
            call_log.append(kwargs)
            raise req.exceptions.SSLError("certificate verify failed")

        with (
            patch.dict(os.environ, _DUMMY_ENV),
            patch("cwa_scraper.requests.get", side_effect=tracking_get),
        ):
            result = cwa.main(["--out-dir", tempfile.mkdtemp()])

        self.assertEqual(result, cwa.EXIT_TLS)
        self.assertEqual(len(call_log), 1, f"Expected 1 request call, got {len(call_log)}")
        for call_kwargs in call_log:
            self.assertNotEqual(
                call_kwargs.get("verify"), False,
                "verify=False was passed to requests.get!"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Timeout / Connection Error → EXIT_NETWORK (4)
# ─────────────────────────────────────────────────────────────────────────────
class TestNetworkErrors(unittest.TestCase):

    def test_timeout_exits_network(self):
        import requests as req
        with (
            patch.dict(os.environ, _DUMMY_ENV),
            patch("cwa_scraper.requests.get", side_effect=req.exceptions.Timeout()),
        ):
            result = cwa.main(["--out-dir", tempfile.mkdtemp()])
        self.assertEqual(result, cwa.EXIT_NETWORK)

    def test_connection_error_exits_network(self):
        import requests as req
        with (
            patch.dict(os.environ, _DUMMY_ENV),
            patch("cwa_scraper.requests.get", side_effect=req.exceptions.ConnectionError()),
        ):
            result = cwa.main(["--out-dir", tempfile.mkdtemp()])
        self.assertEqual(result, cwa.EXIT_NETWORK)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _mock_http_response(status_code, json_data=None, content=None):
    import requests as req
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.ok = status_code < 400
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError(f"{status_code} Error")
    else:
        mock_resp.raise_for_status.return_value = None

    if json_data is not None:
        mock_resp.json.return_value = json_data
        mock_resp.content = json.dumps(json_data).encode()
        mock_resp.text = json.dumps(json_data)
    elif content is not None:
        raw = content if isinstance(content, bytes) else content.encode()
        mock_resp.content = raw
        mock_resp.text = raw.decode()
        mock_resp.json.side_effect = ValueError("Not JSON")
    return mock_resp


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: HTTP 401 / 404 / 500 → EXIT_HTTP (5)
# ─────────────────────────────────────────────────────────────────────────────
class TestHttpErrors(unittest.TestCase):

    def _run(self, status, json_data=None, content=None):
        resp = _mock_http_response(status, json_data=json_data, content=content)
        with (
            patch.dict(os.environ, _DUMMY_ENV),
            patch("cwa_scraper.requests.get", return_value=resp),
        ):
            return cwa.main(["--out-dir", tempfile.mkdtemp()])

    def test_401_exits_http(self):
        self.assertEqual(self._run(401), cwa.EXIT_HTTP)

    def test_404_exits_http(self):
        self.assertEqual(self._run(404), cwa.EXIT_HTTP)

    def test_500_exits_http(self):
        self.assertEqual(self._run(500), cwa.EXIT_HTTP)

    def test_cwa_success_false_bool_exits_http(self):
        """CWA success=false (bool) → EXIT_HTTP (5)."""
        json_data = {"success": False, "message": "Unauthorized"}
        self.assertEqual(self._run(200, json_data=json_data), cwa.EXIT_HTTP)

    def test_cwa_success_false_str_exits_http(self):
        """CWA success='false' (string) → EXIT_HTTP (5)."""
        json_data = {"success": "false", "message": "Bad request"}
        self.assertEqual(self._run(200, json_data=json_data), cwa.EXIT_HTTP)


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Invalid JSON → EXIT_PARSE (6); NO file; NO success message
# ─────────────────────────────────────────────────────────────────────────────
class TestInvalidJson(unittest.TestCase):

    def test_invalid_json_exits_parse_no_file_no_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = b"THIS IS NOT VALID JSON!!!"
        mock_resp.text = "THIS IS NOT VALID JSON!!!"
        mock_resp.json.side_effect = ValueError("No JSON")

        captured_stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as out_dir:
            with (
                patch.dict(os.environ, _DUMMY_ENV),
                patch("cwa_scraper.requests.get", return_value=mock_resp),
                patch("sys.stdout", captured_stdout),
            ):
                result = cwa.main(["--out-dir", out_dir])

            self.assertEqual(result, cwa.EXIT_PARSE)
            files = list(pathlib.Path(out_dir).glob("*"))
            self.assertEqual(len(files), 0, f"Output file created on invalid JSON: {files}")

        stdout_text = captured_stdout.getvalue()
        for word in ["成功", "finished successfully", "downloaded", "Saved"]:
            self.assertNotIn(word, stdout_text, f"Success indicator '{word}' found in stdout")


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: File/Dir Write Failure → EXIT_WRITE (7)
# ─────────────────────────────────────────────────────────────────────────────
class TestWriteFailure(unittest.TestCase):

    def test_dir_creation_failure_exits_write(self):
        """makedirs OSError → EXIT_WRITE (7)."""
        valid_json = {"records": {"datasetInfo": {"datasetName": "Test"}}}
        mock_resp = _mock_http_response(200, json_data=valid_json)
        with (
            patch.dict(os.environ, _DUMMY_ENV),
            patch("cwa_scraper.requests.get", return_value=mock_resp),
            patch("cwa_scraper.os.makedirs", side_effect=OSError("Permission denied")),
        ):
            result = cwa.main(["--out-dir", "/nonexistent_xyz_abc"])
        self.assertEqual(result, cwa.EXIT_WRITE)

    def test_file_open_failure_exits_write(self):
        """File open OSError → EXIT_WRITE (7)."""
        valid_json = {"records": {"datasetInfo": {"datasetName": "Test"}}}
        mock_resp = _mock_http_response(200, json_data=valid_json)

        _real_open = open

        def _patched_open(path, *args, **kwargs):
            if str(path).endswith(".json"):
                raise OSError("Simulated write failure")
            return _real_open(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as out_dir:
            with (
                patch.dict(os.environ, _DUMMY_ENV),
                patch("cwa_scraper.requests.get", return_value=mock_resp),
                patch("builtins.open", side_effect=_patched_open),
            ):
                result = cwa.main(["--out-dir", out_dir])
        self.assertEqual(result, cwa.EXIT_WRITE)


# ─────────────────────────────────────────────────────────────────────────────
# Tests 8 & 9: JSON/XML Success → EXIT_OK (0); file created
# ─────────────────────────────────────────────────────────────────────────────
class TestSuccessCases(unittest.TestCase):

    def test_json_success_exits_ok_file_created(self):
        valid_json = {"records": {"datasetInfo": {"datasetName": "Test"}, "location": []}}
        mock_resp = _mock_http_response(200, json_data=valid_json)
        with tempfile.TemporaryDirectory() as out_dir:
            with (
                patch.dict(os.environ, _DUMMY_ENV),
                patch("cwa_scraper.requests.get", return_value=mock_resp),
            ):
                result = cwa.main(["--out-dir", out_dir])
            self.assertEqual(result, cwa.EXIT_OK)
            self.assertGreater(
                len(list(pathlib.Path(out_dir).glob("*.json"))), 0,
                "No JSON output file created on success"
            )

    def test_xml_success_exits_ok_file_created(self):
        xml_bytes = b"<?xml version='1.0'?><data><item>test</item></data>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = xml_bytes
        mock_resp.text = xml_bytes.decode()

        with tempfile.TemporaryDirectory() as out_dir:
            with (
                patch.dict(os.environ, _DUMMY_ENV),
                patch("cwa_scraper.requests.get", return_value=mock_resp),
            ):
                result = cwa.main(["--format", "XML", "--out-dir", out_dir])
            self.assertEqual(result, cwa.EXIT_OK)
            self.assertGreater(
                len(list(pathlib.Path(out_dir).glob("*.xml"))), 0,
                "No XML output file created on success"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Environment Key preferred over CLI key
# ─────────────────────────────────────────────────────────────────────────────
class TestKeyResolutionPriority(unittest.TestCase):

    def test_env_key_wins_over_cli_key(self):
        env_key = "CWA-ENV-KEY-WINS"
        cli_key = "CWA-CLI-KEY-LOSES"
        args = cwa.parse_arguments(["-k", cli_key])
        with patch.dict(os.environ, {"CWA_API_KEY": env_key}):
            result = cwa.resolve_api_key(args)
        self.assertEqual(result, env_key, "Environment key must take priority over CLI key")

    def test_env_key_no_warning(self):
        """Environment key must NOT trigger the CLI warning."""
        env_key = "CWA-ENV-KEY-NO-WARNING"
        args = cwa.parse_arguments([])
        captured_stderr = io.StringIO()
        with (
            patch.dict(os.environ, {"CWA_API_KEY": env_key}),
            patch("sys.stderr", captured_stderr),
        ):
            result = cwa.resolve_api_key(args)
        self.assertEqual(result, env_key)
        self.assertNotIn("warning", captured_stderr.getvalue().lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
