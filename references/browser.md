# Browser consultation

Use [Claude](https://claude.ai/) or [Gemini](https://gemini.google.com/)
when the CLI cannot use the intended account or when the task benefits from a
web-only capability, including supported YouTube content analysis. Follow the
shared privacy and result-verification rules in `../SKILL.md`.

## Browser and account

Use the supported `mcp__cua_repl` browser tools. Select the relevant browser or
tab using its documented entry points, then read the returned control
documentation before interacting. Reuse an existing sign-in and follow the
tool's browser-selection rules. Prefer the browser already signed into the
intended service.

Before submitting a prompt, verify the configured intended account email in the service's own
account menu or settings. A display name or another Google service's account
does not establish the active account. For Claude, also verify any active
organization is the intended destination. Complete ordinary authorized sign-in
through supported tools. If user authentication input is required, leave the
official flow available for the user; do not inspect browser session stores or
request passwords in chat.

Inspect the current plan, model picker, and relevant effort controls. A model's
own description of itself is not verification.

- **Claude:** Select the latest available general-purpose Opus with **High
  effort**. Honor an explicitly requested model, effort, or mode.
  Use maximum effort or Research mode only when requested or
  warranted by the task. If Opus is unavailable, use the available
  general-purpose default and report the observed model and limitation.
- **Gemini:** Select the latest available general-purpose Flash with **High
  effort**. Honor an explicitly requested effort. The UI may
  call it Flash or Fast; inspect the picker for the actual version. Use
  Flash-Lite, Pro, or a specialized model only when requested.
  If the version is omitted, check current official Google documentation and
  report the observed UI label separately from the documented version.

Recheck the live account, plan, model picker, and effort controls on each task.
Do not treat a previous observation as a permanent model pin or subscription
assumption.

Use the existing account's available plan. Do not enable paid extra usage, buy
an upgrade, or connect additional apps merely to unblock consultation. Report
an access or quota limitation precisely and continue other authorized work.

## Prompt and completion

Start a fresh chat for each unrelated task and reuse it for focused follow-up
questions. Give a bounded question, relevant public URLs, decision constraints,
and the evidence needed.

Keep internet search and relevant tools available, including in retries and
follow-ups. Never instruct either provider to avoid search or tools. For
current facts, explicitly ask it to search the web and provide direct source
URLs, relevant publication or update dates, uncertainty, and distinctions
between sourced facts and inferences. Prefer primary sources for technical
claims. Inspect visible search activity and source controls; an answer alone
does not prove search occurred.

In Claude, enable Web search if the composer exposes that toggle. A missing
toggle does not establish that search is unavailable; consult
[Claude's web search guidance](https://support.claude.com/en/articles/10684626-enable-and-use-web-search)
when the controls are unclear. Direct URL retrieval and web search are distinct;
record a URL access failure explicitly.

Allow at least **10 minutes** after submission before treating an otherwise
error-free response as stalled, and continue while visible search, thinking,
or streaming progresses. Observe progress at **30-60 second** intervals and
continue useful independent work between checks. A blank answer area or search
indicator is not a failure. Retry or narrow the prompt only after an explicit
error, access/quota failure, or at least 10 minutes with no observable progress.
Inspect the latest page state first and avoid duplicate submissions while the
original is running. Honor a shorter user deadline or cancellation.

Read the completed response and source controls. Capture actual destination
URLs rather than citation numbers or search snippets. Use a focused follow-up
to resolve a missing source or access limitation, then stop when further
consultation adds little value. Keep research tabs temporary unless the user asks
to retain them.

## YouTube content and timestamps

Provide the public video URL and request its title, channel, relevant
timestamps, supporting details, and an explicit account of what was accessed:
video content, a transcript, or only metadata and search results. Neither a URL
nor an apparently detailed answer proves content access. CLI access does not
establish the same video capabilities as a provider's web app.

**Gemini:** Prefer its web app for video analysis when the live interface
supports access. A discovery or web-search response may use only metadata; send
the direct video URL in a focused follow-up when content analysis is needed.
If the content is inaccessible, require that limitation. Gemini may put a
timestamp inside a Google Search link; cite the verified original video with
its time offset instead.

**Claude:** Do not assume native video access. Its
[upload documentation](https://support.claude.com/en/articles/8241126-upload-files-to-claude)
does not establish YouTube video analysis. If direct access fails, supply a
public transcript or relevant excerpts obtained through supported tools when
authorized, identify that material, and preserve the original URL and
timestamps.

Never accept guessed timestamps or invented quotes. For discovery, request
actual video URLs and verify selected videos. Check important details against
the accessible video or transcript before using them in the final answer, and
state any remaining access limitation.
