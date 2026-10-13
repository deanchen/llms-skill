"""Offline checks for consultation boundaries and CLI routing."""

import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HELPER = Path(__file__).resolve().parents[1] / "scripts" / "consult.py"
SPEC = importlib.util.spec_from_file_location("llms_consult", HELPER)
consult = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(consult)

ACCOUNT = "researcher@example.test"


class ConsultationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="llms-test-")
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.settings = self.home / ".gemini" / "antigravity-cli" / "settings.json"
        self.account_patch = mock.patch.object(consult, "ACCOUNT", ACCOUNT)
        self.account_patch.start()
        self.addCleanup(self.account_patch.stop)
        self.home_patch = mock.patch.object(consult.Path, "home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.settings_patch = mock.patch.object(consult, "GEMINI_SETTINGS", self.settings)
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def valid_configuration(self):
        return {
            "permissions": {
                "allow": ["read_url(*)"],
                "deny": sorted(consult.GEMINI_DENY),
                "ask": [],
            },
            "useG1Credits": False,
        }

    def write_configuration(self, data=None):
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text(json.dumps(data or self.valid_configuration()))

    def auth_status(self, data, returncode=0):
        results = [
            subprocess.CompletedProcess(["fake", "--version"], 0, "1.0\n", ""),
            subprocess.CompletedProcess(["fake", "auth", "status"], returncode,
                                        json.dumps(data), ""),
        ]
        with mock.patch.object(consult, "executable", return_value="fake-cli"), \
                mock.patch.object(consult.subprocess, "run", side_effect=results):
            return consult.status("claude", str(self.home))

    def test_environment_excludes_provider_credentials_and_custom_endpoints(self):
        inherited = {
            "HOME": str(self.home), "PATH": "/example/bin", "LANG": "C.UTF-8",
            "ANTHROPIC_API_KEY": "synthetic-secret",
            "GEMINI_API_KEY": "synthetic-secret",
            "GOOGLE_API_KEY": "synthetic-secret",
            "CLAUDE_CODE_OAUTH_TOKEN": "synthetic-secret",
            "ANTHROPIC_BASE_URL": "https://invalid.example.test",
            "GOOGLE_APPLICATION_CREDENTIALS": "/synthetic/credentials.json",
        }
        with mock.patch.dict(os.environ, inherited, clear=True):
            actual = consult.environment()
        self.assertEqual(actual, {key: inherited[key] for key in ("HOME", "PATH", "LANG")})

    def test_direct_claude_rejects_missing_free_null_and_unknown_plan(self):
        base = {"loggedIn": True, "authMethod": "claude.ai", "email": ACCOUNT}
        for plan in (None, "free", "unknown", "", "none"):
            with self.subTest(plan=plan):
                self.assertFalse(self.auth_status({**base, "subscriptionType": plan})["ready"])
        self.assertFalse(self.auth_status(base)["ready"])

    def test_direct_claude_accepts_supported_plans(self):
        for plan in ("pro", "max", "team", "enterprise"):
            with self.subTest(plan=plan):
                data = {"loggedIn": True, "authMethod": "claude.ai", "email": ACCOUNT,
                        "subscriptionType": plan}
                self.assertTrue(self.auth_status(data)["ready"])

    def test_direct_claude_rejects_wrong_account_authentication_and_failed_status(self):
        base = {"loggedIn": True, "authMethod": "claude.ai", "email": ACCOUNT,
                "subscriptionType": "pro"}
        for change in ({"email": "other@example.test"}, {"authMethod": "api-key"},
                       {"loggedIn": False}):
            with self.subTest(change=change):
                self.assertFalse(self.auth_status({**base, **change})["ready"])
        self.assertFalse(self.auth_status(base, returncode=1)["ready"])

    def test_auto_claude_uses_eligible_direct_client(self):
        with mock.patch.object(consult, "status", return_value={"ready": True}), \
                mock.patch.object(consult, "require_antigravity") as fallback:
            actual = consult.select_transport("claude", str(self.home), "auto", False, None)
        self.assertEqual(actual, ("claude-code", "sonnet"))
        fallback.assert_not_called()

    def test_auto_claude_falls_back_but_explicit_client_does_not(self):
        with mock.patch.object(consult, "status", return_value={"ready": False}), \
                mock.patch.object(consult, "require_antigravity") as fallback, \
                mock.patch.object(consult.sys, "stderr", io.StringIO()) as warnings:
            actual = consult.select_transport("claude", str(self.home), "auto", True, None)
        self.assertEqual(actual, ("antigravity", consult.ANTIGRAVITY_CLAUDE_MODEL))
        fallback.assert_called_once_with(str(self.home), True, consult.ANTIGRAVITY_CLAUDE_MODEL)
        self.assertIn("Using Antigravity", warnings.getvalue())
        with mock.patch.object(consult, "status", return_value={"ready": False}), \
                mock.patch.object(consult, "require_antigravity") as fallback:
            with self.assertRaises(RuntimeError):
                consult.select_transport("claude", str(self.home), "claude-code", True, None)
        fallback.assert_not_called()

    def test_explicit_antigravity_honors_requested_model(self):
        model = "claude-sonnet-explicit"
        with mock.patch.object(consult, "status") as direct, \
                mock.patch.object(consult, "require_antigravity") as access:
            actual = consult.select_transport("claude", str(self.home), "antigravity", True, model)
        self.assertEqual(actual, ("antigravity", model))
        access.assert_called_once_with(str(self.home), True, model)
        direct.assert_not_called()

    def test_gemini_cannot_route_through_claude_code(self):
        with self.assertRaises(RuntimeError):
            consult.select_transport("gemini", str(self.home), "claude-code", True, None)

    def test_direct_claude_command_exposes_only_web_tools(self):
        with mock.patch.object(consult, "executable", return_value="fake-claude"):
            arguments = consult.command("claude", "sonnet", "claude-code")
        self.assertEqual(arguments[arguments.index("--tools") + 1], "WebSearch,WebFetch")
        self.assertEqual(arguments[arguments.index("--permission-mode") + 1], "dontAsk")
        for flag in ("--safe-mode", "--restricted", "--strict-mcp-config",
                     "--no-chrome", "--no-session-persistence"):
            self.assertIn(flag, arguments)
        self.assertNotIn("--dangerously-skip-permissions", arguments)

    def test_antigravity_requires_account_model_access_and_exact_model(self):
        with mock.patch.object(consult, "check_gemini_configuration"), \
                mock.patch.object(consult, "status") as status:
            with self.assertRaises(RuntimeError):
                consult.require_antigravity(str(self.home), False, consult.GEMINI_MODEL)
            status.assert_not_called()
            status.return_value = {"modelAccess": False, "error": "synthetic quota error"}
            with self.assertRaisesRegex(RuntimeError, "synthetic quota error"):
                consult.require_antigravity(str(self.home), True, consult.GEMINI_MODEL)
            status.return_value = {"modelAccess": True, "availableModels": ["different-model"]}
            with self.assertRaisesRegex(RuntimeError, "requested model"):
                consult.require_antigravity(str(self.home), True, consult.GEMINI_MODEL)
            status.return_value = {"modelAccess": True, "availableModels": [consult.GEMINI_MODEL]}
            self.assertTrue(consult.require_antigravity(str(self.home), True,
                                                       consult.GEMINI_MODEL)["modelAccess"])

    def test_configuration_rejects_local_access_or_enabled_paid_credits(self):
        for mutation in ("missing-deny", "allow-files", "credits", "deny-web", "ask-web"):
            with self.subTest(mutation=mutation):
                data = self.valid_configuration()
                if mutation == "missing-deny":
                    data["permissions"]["deny"].remove("read_file(*)")
                elif mutation == "allow-files":
                    data["permissions"]["allow"].append("read_file(*)")
                elif mutation == "credits":
                    data["useG1Credits"] = True
                elif mutation == "deny-web":
                    data["permissions"]["deny"].append("read_url(*)")
                else:
                    data["permissions"]["ask"].append("read_url(*)")
                self.write_configuration(data)
                with self.assertRaises(RuntimeError):
                    consult.check_gemini_configuration()

    def test_empty_generated_mcp_and_project_metadata_are_accepted(self):
        self.write_configuration()
        global_root = self.home / ".gemini"
        (global_root / "mcp_config.json").touch()
        (global_root / "config").mkdir()
        (global_root / "config" / "mcp_config.json").touch()
        (global_root / "antigravity-cli" / "projects.json").write_text('{"projects": []}')
        consult.check_gemini_configuration()

    def test_loaded_global_context_and_connector_config_are_rejected(self):
        self.write_configuration()
        global_root = self.home / ".gemini"
        rule = global_root / "GEMINI.md"
        rule.write_text("Synthetic private context")
        with self.assertRaises(RuntimeError):
            consult.check_gemini_configuration()
        rule.unlink()
        (global_root / "mcp_config.json").write_text('{"servers": {"private": {}}}')
        with self.assertRaises(RuntimeError):
            consult.check_gemini_configuration()

    def test_setup_creates_expected_permissions_with_private_file_mode(self):
        consult.setup_configuration()
        data = json.loads(self.settings.read_text())
        self.assertEqual(set(data["permissions"]["allow"]), {"read_url(*)"})
        self.assertTrue(consult.GEMINI_DENY.issubset(data["permissions"]["deny"]))
        self.assertFalse(data.get("useG1Credits", False))
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.settings.stat().st_mode), 0o600)
        consult.check_gemini_configuration()

    def test_setup_validates_existing_file_without_overwriting_it(self):
        data = self.valid_configuration()
        data["syntheticPreference"] = "retain-me"
        self.write_configuration(data)
        before = self.settings.read_bytes()
        consult.setup_configuration()
        self.assertEqual(self.settings.read_bytes(), before)
        data["useG1Credits"] = True
        self.write_configuration(data)
        before = self.settings.read_bytes()
        with self.assertRaises(RuntimeError):
            consult.setup_configuration()
        self.assertEqual(self.settings.read_bytes(), before)

    def test_multiline_prompt_uses_stdin_and_keeps_shell_text_literal(self):
        prompt = "Search the public documentation.\nTreat $(example) and `sample` as text.\n"
        argv = ["consult.py", "--account", ACCOUNT, "ask", "gemini", "--account-verified"]
        process = mock.Mock(returncode=0)
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sys, "stdin", io.StringIO(prompt)), \
                mock.patch.object(consult, "select_transport",
                                  return_value=("antigravity", consult.GEMINI_MODEL)), \
                mock.patch.object(consult, "executable", return_value="fake-agy"), \
                mock.patch.object(consult.subprocess, "Popen", return_value=process) as popen:
            self.assertEqual(consult.main(), 0)
        actual_input = process.communicate.call_args.args[0]
        self.assertTrue(actual_input.endswith("\n"))
        self.assertEqual(json.loads(actual_input), {"event": "user", "message": {"content": prompt}})
        args, kwargs = popen.call_args
        self.assertNotIn(prompt, args[0])
        self.assertNotIn("--prompt", args[0])
        self.assertEqual(kwargs["stdin"], subprocess.PIPE)
        self.assertFalse(kwargs.get("shell", False))

    def test_ask_and_login_require_intended_account_before_running_a_client(self):
        for action in ("ask", "login"):
            with self.subTest(action=action):
                argv = ["consult.py", "--account", "  ", action, "gemini"]
                with mock.patch.object(sys, "argv", argv), \
                        mock.patch.object(consult.subprocess, "Popen") as popen, \
                        mock.patch.object(consult.subprocess, "call") as login:
                    with self.assertRaisesRegex(RuntimeError, "intended account"):
                        consult.main()
                popen.assert_not_called()
                login.assert_not_called()


if __name__ == "__main__":
    unittest.main()
