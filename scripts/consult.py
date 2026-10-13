#!/usr/bin/env python3
"""Run bounded consultations using official account-authenticated CLIs."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ACCOUNT = os.environ.get("LLMS_ACCOUNT", "").strip()
GEMINI_SETTINGS = Path.home() / ".gemini/antigravity-cli/settings.json"
GEMINI_MODEL = "gemini-3.8-flash-low"
ANTIGRAVITY_CLAUDE_MODEL = "claude-sonnet-5-5-medium"
GEMINI_DENY = {
    "read_file(*)", "write_file(*)", "command(*)", "unsandboxed(*)",
    "mcp(*)", "execute_url(*)",
}
CLAUDE_PLANS = {"pro", "max", "team", "enterprise"}


def setup_configuration():
    """Create consultation settings without replacing an existing CLI configuration."""
    if GEMINI_SETTINGS.exists():
        check_gemini_configuration()
        return False
    settings = {
        "permissions": {"deny": sorted(GEMINI_DENY), "allow": ["read_url(*)"]},
        "allowNonWorkspaceAccess": False,
        "useG1Credits": False,
        "enableTelemetry": False,
    }
    GEMINI_SETTINGS.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(GEMINI_SETTINGS, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(settings, output, indent=2)
        output.write("\n")
    return True


def environment():
    # An allowlist avoids API billing, custom endpoints, and inherited plugins.
    keys = ("HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "TERM",
            "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS")
    return {key: os.environ[key] for key in keys if key in os.environ}


def executable(provider):
    name = "agy" if provider == "gemini" else provider
    result = shutil.which(name)
    if not result:
        raise RuntimeError(f"{name} CLI is not installed; see references/cli.md.")
    return result


def gemini_environment():
    env = environment()
    env["TERM"] = "xterm-256color"
    return env


def check_gemini_configuration():
    if not GEMINI_SETTINGS.is_file():
        raise RuntimeError("Antigravity consultation settings are missing; see references/cli.md.")
    settings = json.loads(GEMINI_SETTINGS.read_text())
    if not isinstance(settings, dict):
        raise RuntimeError("Antigravity consultation settings must be a JSON object.")
    permissions = settings.get("permissions", {})
    if not isinstance(permissions, dict):
        raise RuntimeError("Antigravity consultation permissions must be a JSON object.")
    deny = permissions.get("deny", [])
    allow = permissions.get("allow", [])
    ask = permissions.get("ask", [])
    if not all(isinstance(rules, list) and all(isinstance(rule, str) for rule in rules)
               for rules in (deny, allow, ask)):
        raise RuntimeError("Antigravity consultation permission lists are invalid.")
    if not GEMINI_DENY.issubset(deny) or set(allow) != {"read_url(*)"}:
        raise RuntimeError("Antigravity consultation permissions have changed; use the browser.")
    if "read_url(*)" in deny or "read_url(*)" in ask:
        raise RuntimeError("Antigravity web retrieval is blocked; use the browser.")
    if settings.get("useG1Credits", False) is not False:
        raise RuntimeError("Antigravity AI credits must be disabled for consultation.")
    custom_keys = {"modelProvider", "modelProviders", "customModels", "authProvider",
                   "authProviders", "apiKey", "apiBaseUrl", "baseUrl"}
    if custom_keys.intersection(settings):
        raise RuntimeError("Antigravity has a custom model or authentication provider; use the browser.")

    # Check presence only; private rules and customization contents stay unread.
    global_root = Path.home() / ".gemini"
    for name in ("AGENTS.md", "GEMINI.md", "config/AGENTS.md", "config/GEMINI.md"):
        if (global_root / name).exists():
            raise RuntimeError("Antigravity global context or connectors are configured; use the browser.")
    for name in ("mcp_config.json", "config/mcp_config.json"):
        path = global_root / name
        if path.exists() and path.stat().st_size:
            raise RuntimeError("Antigravity global connectors are configured; use the browser.")
    for path in (global_root / "config/rules", global_root / "rules",
                 global_root / "hooks", global_root / "agents",
                 global_root / "skills", global_root / "antigravity-cli/plugins",
                 global_root / "antigravity-cli/rules", global_root / "antigravity-cli/hooks",
                 global_root / "antigravity-cli/agents", global_root / "antigravity-cli/skills"):
        if path.exists() and (not path.is_dir() or next(path.iterdir(), None) is not None):
            raise RuntimeError("Antigravity global customizations are configured; use the browser.")


def status(provider, cwd):
    binary = executable(provider)
    env = gemini_environment() if provider == "gemini" else environment()
    version = subprocess.run([binary, "--version"], cwd=cwd, env=env,
                             capture_output=True, text=True, timeout=30)
    if version.returncode:
        raise RuntimeError(f"{provider} version check failed: {version.stderr.strip()}")
    result = {"provider": provider, "version": version.stdout.strip(),
              "binary": binary, "accountConfigured": bool(ACCOUNT)}
    if provider == "claude":
        auth = subprocess.run([binary, "auth", "status"], cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=30)
        try:
            data = json.loads(auth.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError("Claude auth status did not return JSON.") from error
        if not isinstance(data, dict):
            raise RuntimeError("Claude auth status did not return a JSON object.")
        for key in ("loggedIn", "authMethod", "email", "subscriptionType", "orgId", "orgName"):
            if key in data:
                result[key] = data[key]
        result["ready"] = bool(ACCOUNT and auth.returncode == 0 and data.get("loggedIn") and
                               data.get("email") == ACCOUNT and
                               data.get("authMethod") == "claude.ai" and
                               str(data.get("subscriptionType", "")).lower() in CLAUDE_PLANS)
    else:
        models = subprocess.run([binary, "models"], cwd=cwd, env=env,
                                capture_output=True, text=True, timeout=30)
        result["modelAccess"] = models.returncode == 0
        result["modelMetadata"] = models.stdout.strip()
        result["availableModels"] = sorted(set(
            re.findall(r"\b(?:claude|gemini)-[a-z0-9._-]+\b", models.stdout)))
        result["transport"] = "antigravity"
        if models.returncode:
            result["error"] = models.stderr.strip() or "Antigravity model access check failed."
        result["accountVerified"] = False
        result["accountVerificationRequired"] = True
        result["ready"] = False
        result["note"] = (
            f"Model access does not identify the account. Verify {ACCOUNT or 'the intended account'} in the "
            "live interactive CLI header or a fresh official CLI OAuth sign-in "
            "flow, then pass --account-verified to ask.")
        try:
            check_gemini_configuration()
            result["consultationConfigured"] = True
        except (RuntimeError, OSError, ValueError) as error:
            result["consultationConfigured"] = False
            result["configError"] = str(error)
    return result


def require_antigravity(cwd, account_verified, model):
    if not account_verified:
        raise RuntimeError(
            f"Verify {ACCOUNT} in the live interactive Antigravity CLI header or a "
            "fresh official CLI OAuth sign-in flow before using --account-verified; "
            "model access cannot verify identity.")
    check_gemini_configuration()
    info = status("gemini", cwd)
    if not info["modelAccess"]:
        raise RuntimeError(info.get("error", "Antigravity model access is unavailable."))
    if model not in info["availableModels"]:
        raise RuntimeError(f"Antigravity does not list the requested model {model}; use a listed model or the browser.")
    return info


def select_transport(provider, cwd, transport, account_verified, model):
    if provider == "gemini" and transport == "claude-code":
        raise RuntimeError("The claude-code transport supports Claude only.")
    if transport == "antigravity" or provider == "gemini":
        selected_model = model or (GEMINI_MODEL if provider == "gemini" else ANTIGRAVITY_CLAUDE_MODEL)
        require_antigravity(cwd, account_verified, selected_model)
        return "antigravity", selected_model

    try:
        info = status("claude", cwd)
        if info["ready"]:
            return "claude-code", model or "sonnet"
        reason = "Claude Code has no eligible login for the intended account."
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        reason = f"Claude Code is unavailable: {error}"
    if transport == "claude-code":
        raise RuntimeError(f"{reason} Run this helper's Claude login command or use the verified web account.")
    selected_model = model or ANTIGRAVITY_CLAUDE_MODEL
    require_antigravity(cwd, account_verified, selected_model)
    print(f"LLMs: {reason} Using Antigravity model {selected_model}.", file=sys.stderr)
    return "antigravity", selected_model


def command(provider, model, transport="auto"):
    if provider == "gemini" and transport == "claude-code":
        raise RuntimeError("The claude-code transport supports Claude only.")
    if transport == "antigravity" or provider == "gemini":
        binary = executable("gemini")
        selected_model = model or (GEMINI_MODEL if provider == "gemini" else ANTIGRAVITY_CLAUDE_MODEL)
        return [binary, "--model", selected_model, "--disable-slash-commands",
                "--input-format", "stream-json", "--output-format", "stream-json",
                "--print-timeout", "0"]
    binary = executable("claude")
    return [binary, "--safe-mode", "--restricted", "--print",
            "--model", model or "sonnet", "--tools", "WebSearch,WebFetch",
            "--allowedTools", "WebSearch", "WebFetch", "--permission-mode", "dontAsk",
            "--settings", json.dumps({"disableAllHooks": True,
                                      "disableClaudeAiConnectors": True}),
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--no-chrome", "--no-session-persistence",
            "--output-format", "stream-json", "--verbose"]


def main():
    global ACCOUNT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", default=ACCOUNT,
                        help="Intended account email; defaults to LLMS_ACCOUNT")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("setup", help="Create consultation settings if absent; never overwrite existing settings")
    check = sub.add_parser("status", help="Show non-secret CLI/account metadata")
    check.add_argument("provider", nargs="?", choices=("claude", "gemini"))
    login = sub.add_parser("login", help="Start the official account login flow")
    login.add_argument("provider", choices=("claude", "gemini"))
    ask = sub.add_parser("ask", help="Read question from stdin or --prompt")
    ask.add_argument("provider", choices=("claude", "gemini"))
    ask.add_argument("--prompt")
    ask.add_argument("--model", help="Explicit provider model; otherwise Sonnet/Flash")
    ask.add_argument("--transport", choices=("auto", "claude-code", "antigravity"),
                     default="auto", help="CLI transport; auto prefers Claude Code for Claude")
    ask.add_argument("--account-verified", action="store_true",
                     help="Caller verified the Antigravity account in its live header or fresh OAuth sign-in")
    args = parser.parse_args()
    ACCOUNT = args.account.strip()
    if args.action in ("ask", "login") and not ACCOUNT:
        raise RuntimeError("Set LLMS_ACCOUNT or --account to the intended account email.")
    if args.action == "setup":
        created = setup_configuration()
        print("Consultation settings created." if created else "Existing consultation settings verified; unchanged.")
        return 0
    with tempfile.TemporaryDirectory(prefix="llms-") as cwd:
        if args.action == "status":
            results = []
            for provider in ([args.provider] if args.provider else ("claude", "gemini")):
                try:
                    results.append(status(provider, cwd))
                except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
                    results.append({"provider": provider, "ready": False,
                                    "error": str(error)})
            print(json.dumps(results, indent=2))
            return 0 if all(item["ready"] for item in results) else 1
        if args.action == "login":
            if args.provider == "claude":
                cmd = [executable("claude"), "auth", "login", "--email", ACCOUNT]
                env = environment()
            else:
                env = gemini_environment()
                cmd = [executable("gemini")]
            return subprocess.call(cmd, cwd=cwd, env=env)
        prompt = args.prompt if args.prompt is not None else sys.stdin.read()
        if not prompt.strip():
            raise RuntimeError("Provide a consultation question on stdin or with --prompt.")
        transport, model = select_transport(args.provider, cwd, args.transport,
                                            args.account_verified, args.model)
        if transport == "antigravity":
            prompt = json.dumps({"event": "user", "message": {"content": prompt}}) + "\n"
        env = gemini_environment() if transport == "antigravity" else environment()
        process = subprocess.Popen(command(args.provider, model, transport), cwd=cwd,
                                   env=env, stdin=subprocess.PIPE, text=True)
        try:
            process.communicate(prompt)
        except KeyboardInterrupt:
            process.terminate()
            process.wait()
            return 130
        return process.returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"LLMs: {error}", file=sys.stderr)
        sys.exit(1)
