# CLI consultation

## Supported clients

Use **Antigravity CLI (`agy`)** for Gemini and, when available, Claude Opus through the user's existing Google plan. Google retired individual-account Gemini CLI access on June 18, 2026. A successful legacy `gemini` OAuth login does not restore that service; `UNSUPPORTED_CLIENT` means use Antigravity or the web app.

Use **Claude Code (`claude`)** when the separate Claude account has an eligible plan. Claude Code excludes Free accounts. Claude.ai remains the fallback for the intended Claude service. Do not use Console/API billing to bypass an account-plan limitation.

On macOS, install the supported clients through Homebrew:

```sh
HOMEBREW_NO_INSTALL_CLEANUP=1 brew install --cask antigravity-cli claude-code
HOMEBREW_NO_INSTALL_CLEANUP=1 brew upgrade --cask antigravity-cli claude-code
agy --version
claude --version
```

Honor installed help and current official docs after updates. Do not migrate legacy extensions, MCP servers, skills, or global context during consultation setup. API keys, custom endpoints, and paid overage are outside this workflow.

## Account and model checks

Run the helper from the installed skill directory. Set `LLMS_ACCOUNT` to the intended account email, or use the global `--account` option before the subcommand:

```sh
export LLMS_ACCOUNT='you@example.com'
python3 scripts/consult.py setup
python3 scripts/consult.py login gemini
python3 scripts/consult.py status
agy models
```

`login gemini` launches interactive `agy` in an empty directory. Select Google OAuth, verify the account configured in `LLMS_ACCOUNT` or `--account` in the official account chooser, and complete its code flow. The provider stores the session in the OS keyring; never inspect tokens or session stores. A fresh official CLI sign-in with the verified email or the live CLI header establishes identity. `agy models` proves cached model access, but does not identify the account. The helper requires `--account-verified` as the caller's assertion of that check, and reports account verification separately from model access.

If an OAuth code needs transfer, use the supported browser's Copy control and pass it directly to the CLI without printing it or putting it in tool arguments. Browser automation can have a virtual clipboard separate from the host clipboard. Transfer privately through the consuming process and restore prior clipboard contents. Remove temporary setup controllers after use. If actual user authentication input is required, leave the official flow available and continue independent work.

For direct Claude Code:

```sh
python3 scripts/consult.py login claude
claude auth status
```

Check the email, account authentication, organization if present, and subscription. The helper permits direct use only when the official status succeeds with the intended email and `claude.ai` authentication. It exposes non-secret organization metadata. A Claude Free account should use the web app or available Opus access through the Google account.

Run `agy models` to check exact identifiers. The defaults are `gemini-3.8-flash-high` and `claude-opus-5-5-high`, both **High effort**. Refresh these defaults when a newer general Flash or Opus becomes available. Direct Claude Code uses the `opus` alias with `--effort high`. Honor an explicitly requested effort; the model's own claimed identity is not verification.

## Consultation settings

`python3 scripts/consult.py setup` creates this configuration at `~/.gemini/antigravity-cli/settings.json` only when no file exists. Existing settings are validated and never overwritten:

```json
{
  "permissions": {
    "deny": [
      "read_file(*)", "write_file(*)", "command(*)", "unsandboxed(*)",
      "mcp(*)", "execute_url(*)"
    ],
    "allow": ["read_url(*)"]
  },
  "allowNonWorkspaceAccess": false,
  "useG1Credits": false,
  "enableTelemetry": false
}
```

For an existing installation, review and merge only the consultation fields deliberately. These permissions apply to that Antigravity installation and can affect its other uses. Preserve unrelated settings and use the browser when global private context or connectors make the CLI unsuitable.

## Helper operation

```sh
python3 scripts/consult.py ask gemini --account-verified --prompt 'Search current official documentation for the public question and give direct URLs.'
python3 scripts/consult.py ask claude --transport antigravity --account-verified --prompt 'Analyze the public question and identify uncertainty.'
```

Use stdin for long prompts or task-relevant private context authorized by the main skill. `--transport auto` selects Antigravity for Gemini, and authenticated Claude Code for Claude with available Antigravity Opus as its fallback. Explicit `--transport claude-code` or `--transport antigravity` controls the account route. The helper announces fallback, checks exact model availability, and never substitutes a different model after an error. `--model` honors a requested identifier.

Every consultation starts in an empty temporary directory with a minimal inherited environment, excluding API keys and custom endpoints. Antigravity reads `~/.gemini/antigravity-cli/settings.json`; this setup denies file reads/writes, commands, MCP, and browser actuation while allowing public URL retrieval. `useG1Credits` is false by default; the helper rejects paid overage if enabled. The CLI may omit false defaults when serializing its settings.

The helper checks consultation permissions and refuses automatically loaded global rules/customizations. Empty CLI-generated MCP files and project metadata are ordinary runtime state, not private prompt context. These are tool permissions, not an OS sandbox. Review user changes to these settings for consultation scope; the helper does not overwrite them.

Claude Code uses `--safe-mode --restricted`, only `WebSearch,WebFetch`, explicit web-tool permissions, empty MCP configuration, disabled account connectors, and no disk session persistence. Avoid `--bare` for subscription consultation because it skips OAuth/keychain and requires API/provider credentials.

Output is the client's stream of JSON events. Inspect the actual model, successful search/fetch tool results, final status, errors, and permission notices. Antigravity can soft-deny a tool and still exit zero, so exit status alone is insufficient. A model response claiming search does not establish retrieval. Resolve grounding redirects before citing original URLs. Installed `--print-timeout 0` waits for completion; preserve the main skill's response-patience guidance.

Antigravity may save fetched page text under its `brain` cache and ask the model to inspect that file. Local reads remain denied, including these cache files. When this occurs, Codex retrieves the public source independently and supplies a bounded excerpt or synopsis with the original URL in a follow-up. Distinguish model-visible search summaries, successfully fetched pages, and actual inspected page text.

Web video access is distinct from CLI URL retrieval. Use the Gemini web app for supported YouTube analysis and verify the actual material accessed.

## Development verification

On 2026-10-12, Claude Code 2.1.287 and Antigravity 1.3.3 were tested. Gemini 3.8 Flash Low and Claude Sonnet 5.5 Medium completed live CLI consultations with search/fetch events and `SUCCESS` results. A synthetic sentinel read and a shell command were denied by policy. Sonnet reported the saved-source inspection limitation described above; a follow-up with Codex-supplied public evidence succeeded and distinguished supplied material from the model's own retrieval. The corresponding web consultations also completed. Direct Claude Code consultation was not tested with an eligible subscription. Recheck access and models on future tasks.

On 2026-10-19 (America/Los_Angeles), Antigravity CLI 1.4.3 listed `claude-opus-5-5-high`, and its live interactive header confirmed the intended signed-in account. The helper was invoked with `--transport antigravity --account-verified` and no `--model` override; its initialization event selected `claude-opus-5-5-high`. A public Python sorting question completed with `SUCCESS` in about 15 seconds. The event stream showed a completed `search_web` call, and the answer matched the official Python Sorting HOWTO when independently checked by Codex. An attempted shell-based page fetch was denied by the configured `unsandboxed(*)` rule; Opus disclosed that its answer relied on search results. This verifies Opus selection, a completed response, web search, and that command denial for this test; it does not verify direct page retrieval through the allowed URL tool, every permission boundary, or direct Claude Code access. Recheck the account and model availability on each use.

## Official references

- [Google's Gemini CLI transition](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)
- [Antigravity installation and authentication](https://antigravity.google/docs/cli/install/)
- [Antigravity headless input, output, and errors](https://antigravity.google/docs/cli/headless/)
- [Antigravity permissions](https://antigravity.google/docs/permissions/)
- [Antigravity global rules](https://antigravity.google/docs/rules/)
- [Antigravity models](https://antigravity.google/docs/models/)
- [Claude Code setup](https://code.claude.com/docs/en/setup)
- [Claude authentication](https://code.claude.com/docs/en/authentication)
- [Claude CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Claude programmatic use](https://code.claude.com/docs/en/headless)
