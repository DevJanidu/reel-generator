# Direct AI providers

The existing station supports `codex_cli`, `claude_cli`, `manual` and `openai-compatible`. Choose and save a provider in Settings. Codex CLI is the preferred automatic provider; account authentication and a per-workspace Windows isolation probe must pass. Failures never silently change provider, authentication or billing.

## Codex CLI

Tested binary: **codex-cli 0.166.0**. Detection checks the native executable/version and `codex login status` without logging token values. Generation uses documented `codex exec` with stdin, JSON Schema output, JSON events, ephemeral sessions, ignored user config/rules, no daemon and a read-only model-tool sandbox. Shell, unified execution, hooks, plugins, apps, subagents, web search and shell snapshots are disabled. Unexpected tool-execution events fail validation.

Live Studio drains JSONL stdout asynchronously in the isolated worker and normalizes only allowlisted session/turn/response status metadata into episode-local activity journals. Thinking, response text and tool arguments are never forwarded to SSE. The controller still validates the complete structured result before reporting stage/file completion. Page refresh and reconnect restore the journal through `/api/activity` and `/api/activity/stream`; no fabricated AI percentages are shown.

The entire CLI process also runs inside verified Windows MXC; a tool sandbox alone is not treated as the OS boundary. The model returns structured content, never filenames or executable commands. The trusted controller validates the Pydantic contract and saves fixed episode-relative files.

An authenticated ChatGPT Codex login needs **no separate API key**. A normal shared Codex home needs writable state and failed under strict isolation. Following OpenAI's documented cache-provisioning pattern, the controller provisions the installed **file-based** cache into a private per-job Codex home. It does not parse credentials, turn them into an API integration, log them, change the original store or copy refreshed credentials back. Owner-only NTFS ACLs protect the private home; MXC makes its auth file read-only; private files are not served by HTTP. The copy is removed after completion and interrupted copies are cleaned on controller startup. If authentication expires and cannot refresh read-only, refresh/login using the official CLI and retry. A keyring-only cache is reported unsupported rather than extracted.

Official references: [CLI/schema options](https://learn.chatgpt.com/docs/cli/reference), [authentication and cache provisioning](https://learn.chatgpt.com/docs/auth?surface=cli), [Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox).

## Claude Code CLI

Login is reported separately from application-integration eligibility. Dashboard automation needs one explicitly configured credential; both modes use disabled tools, strict empty MCP configuration, no session persistence, JSON Schema output and denied prompts, inside the same native boundary.

The installed **Claude Code 2.1.318** supports `--output-format stream-json --verbose`; this adapter parses its result envelope separately from Codex JSONL. A real authorized short structured streaming diagnostic passed during the Live Studio upgrade. Authentication failures remain unavailable/manual states, with no automatic provider or billing substitution.

- **Your subscription:** run `claude setup-token` yourself, then set **CLAUDE_CODE_OAUTH_TOKEN** in `.env` and restart. Bare mode ignores this token, so the job runs `claude -p --setting-sources ""` with an empty private per-job `CLAUDE_CONFIG_DIR` and CLAUDE.md/auto memory disabled. Usage counts against your plan's limits. This is for the owner's personal use on their own machine: do not share the station or token with other people.
- **API key:** set **ANTHROPIC_API_KEY** to authorize separately billed use through `claude --bare -p`. It takes precedence when both are set.

With neither, the Test button reports AUTHENTICATION and explains the requirement. Manual export/import remains available.

The token is passed only to Claude provider jobs, never written to request files and redacted from errors. The adapter never reads or copies Claude login files, offers Claude.ai sign-in, converts subscription tokens or silently changes billing. Bedrock/Vertex/Foundry/key-helper adapters are not implemented. Official references: [programmatic/bare mode](https://code.claude.com/docs/en/headless), [credential-use restrictions](https://code.claude.com/docs/en/legal-and-compliance).

## Manual and API

Manual exports the same complete skill/master/task messages and schema, then validates explicit JSON import against its pinned request. It never simulates AI execution. API mode retains the explicit OpenAI-compatible `/chat/completions` adapter using ODD_AI_API_KEY and a configured model; it does not reuse CLI credentials. Keys are not included in request files or dashboard responses.

## Configuration and tests

```dotenv
ODD_AI_PROVIDER=codex_cli
ODD_CODEX_COMMAND=codex
ODD_CLAUDE_COMMAND=claude
ODD_AI_TIMEOUT_SECONDS=300
ODD_AI_MAX_CONCURRENT_JOBS=1
ODD_AI_CONTEXT_TOKENS=200000
ODD_AI_OUTPUT_TOKENS=12000
```

Settings persists provider/model/timeout/concurrency independently of environment defaults. Commands remain administrator-controlled environment values. A blank CLI model uses the installed CLI default, labeled honestly in provenance. Unsupported models fail; no substitution occurs. The conservative full-content context bound remains enforced.

Each Test AI Connection button sends a real short nonce/JSON diagnostic to an eligible provider, with all four full skills/master included, and validates the exact response. Installation/login alone is not success. Results distinguish authentication, usage limits, invalid output, timeout and cancellation. Manual reports readiness without claiming a model call.

Create New Reel queues ten ideas; choosing one queues script writing and internal review with automatic providers. The sole approval freezes narration and automatically queues preparation. Every stage rereads pinned full instructions. Local request/response/progress/error/retry records stay in the episode. AI concurrency defaults to one (configurable 1–4); every workspace must pass its own native probe. Conflicting same-episode jobs are rejected/serialized. Rendering stays one job at a time.

Real usage tests are opt-in: `scripts/verify.ps1 -CLI` or `node scripts/ui-smoke.mjs --providers`. Ordinary pytest uses mocks and does not consume model generation usage.
