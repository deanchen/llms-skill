# LLMs

A Codex skill for consulting Claude and Gemini through existing account plans, using official CLIs when available and the web apps when their capabilities fit the task better.

By default, consult all available providers supported by the skill, currently Claude and Gemini, independently and reconcile their answers. An explicit request for a single provider or a subset overrides this default. Each provider uses High effort unless requested otherwise; unavailable providers are reported after trying the supported fallback.

The skill checks account identity and model access, preserves web search and source retrieval, and keeps Codex responsible for verifying evidence and performing authorized actions. It includes guidance for YouTube analysis and for distinguishing retrieved sources from supplied excerpts or model inferences.

## Install

Ask Codex:

> Install the skill from https://github.com/deanchen/llms-skill with the name llms.

Or clone this repository into a new skill directory:

```sh
git clone https://github.com/deanchen/llms-skill.git "${CODEX_HOME:-$HOME/.codex}/skills/llms"
```

An existing skill directory must be preserved or updated intentionally. Invoke the installed skill as `$llms`.

## CLI setup

Python 3.10 or newer is required for the helper; it uses only the standard library. On macOS, install the clients through Homebrew:

```sh
HOMEBREW_NO_INSTALL_CLEANUP=1 brew install --cask antigravity-cli claude-code
```

For other operating systems, follow the official [Antigravity installation guide](https://antigravity.google/docs/cli/install/) and [Claude Code setup guide](https://code.claude.com/docs/en/setup).

Run the following from the repository or installed skill directory. Replace the example email with the account you intend to use:

```sh
export LLMS_ACCOUNT='you@example.com'
python3 scripts/consult.py setup
python3 scripts/consult.py login gemini
python3 scripts/consult.py status
```

`setup` creates consultation permissions only when the Antigravity settings file is absent. If existing settings are incompatible, it reports the problem and leaves them intact. Review [the required configuration](references/cli.md#consultation-settings) before adapting an existing installation.

`login gemini` opens Antigravity's Google OAuth flow. Verify the intended email in that flow or the live CLI header before using `--account-verified`. The flag records a completed account check; model availability alone cannot verify identity.

## Consult

```sh
python3 scripts/consult.py ask gemini --account-verified --prompt 'Search official sources for the difference between list.sort() and sorted(). Include original source URLs.'
python3 scripts/consult.py ask claude --transport antigravity --account-verified --prompt 'Review the public evidence and identify assumptions.'
```

For a single invocation without an exported variable, put `--account you@example.com` before the subcommand. Long prompts and explicitly authorized private context can be supplied on stdin.

Claude defaults to eligible Claude Code account access, with an announced Antigravity Opus fallback when available. Pin `--transport claude-code` or `--transport antigravity` to choose explicitly. `--model` selects an available provider model.

Both providers default to **High effort**: `gemini-3.8-flash-high` and `claude-opus-5-5-high`. Direct Claude Code uses the `opus` alias with `--effort high`. A live Antigravity CLI 1.4.3 test on 2026-10-19 confirmed the default Opus model, successful web search, and a completed response; an attempted shell fetch was denied by the configured permissions. See [verification details](references/cli.md#development-verification) for the observed limits. Models, eligibility, and quota can change; inspect `agy models` and the official client documentation before updating those defaults.

## Scope and limitations

- Uses existing account plans; API keys, paid overage, upgrades, and personal connectors are outside the default workflow.
- Antigravity consultation settings deny local file access, commands, MCP, and browser actuation while allowing public URL retrieval. These settings apply to that CLI installation, so review their effect on other uses.
- Automatic private global context causes the helper to use the browser workflow instead.
- A fetched page saved to the CLI's local cache can be inaccessible under consultation permissions. Codex supplies a bounded public excerpt or uses the browser when needed.
- Browser control tools are provided by the host environment, not by this repository. The helper does not automate browser sign-in or independently verify Antigravity's cached account identity.

See [SKILL.md](SKILL.md), [CLI operations](references/cli.md), and [browser/YouTube operations](references/browser.md).

## Validation

```sh
python3 -m unittest discover -s tests -v
```

Offline tests exercise account checks, transport selection, configuration guards, and stdin prompt handling. During initial development, both models completed public research consultations through Antigravity; live tests also confirmed local file and command denials. The GitHub workflow runs offline tests and makes no provider requests.
