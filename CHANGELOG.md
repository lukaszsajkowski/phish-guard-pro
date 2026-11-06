# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-05

First tagged release: the complete single-user workflow, from pasting a phishing email to an exported intelligence report.

### Added

- Email intake and Profiler agent: paste a phishing email, classify the attack type (including `credential_phishing`), and handle non-phishing input (US-003–US-005).
- Persona Engine: a believable victim persona generated with Faker, seeded per session (US-006).
- Conversation agent: first reply, multi-turn continuation, editable replies, visible agent reasoning, turn counter and session limit; replies in the language of the scammer's latest message (US-007–US-010, US-013–US-015, US-027).
- Human in the loop: every reply is reviewed, edited or copied by the operator before it is sent (US-008, US-009).
- Intel Collector: regex-based IOC extraction (BTC wallets, IBANs, phone numbers, URLs, IP addresses) and the Intel Dashboard (US-011, US-012).
- IOC enrichment: mempool.space and bitcoinabuse for BTC, VirusTotal for URLs/domains, AbuseIPDB for IPs, phone validation, enrichment-aware IOC quality score, enriched exports (US-033–US-040).
- Risk score with a per-component breakdown (US-032).
- Bot unmasking detection and manual session end with a session summary (US-016–US-018).
- Session history: list, detail view, persistence across refreshes, JSON and CSV export (US-019, US-020, US-028–US-031).
- Authentication with Supabase Auth and Row Level Security on all tables (US-001, US-002).
- Basal local decision layer: per-node `off`/`shadow`/`live` modes, decision log, profiler eval CLI and an in-role check for generated replies (US-047–US-050, US-053, US-056).
- GPT token usage logging (US-055).
- UI: light/dark theme (light by default), design token system, redesigned session detail and threat intel panels, responsive layout (US-026, US-041–US-046).
- Repository hygiene: `AGENTS.md`, GitHub Actions CI (backend, frontend, gitleaks), CodeQL, Dependabot, branch protection on `main`, `SECURITY.md`, MIT `LICENSE`.

### Changed

- LLM access goes through provider adapters: `LLM_PROVIDER` selects OpenAI, Anthropic or Ollama. The default model is `gpt-6-luna` with `gpt-5.4-mini` as fallback, replacing `gpt-4o` / `gpt-4o-mini`. Existing `OPENAI_PRIMARY_MODEL` / `OPENAI_FALLBACK_MODEL` settings are still honoured.
- Accessibility fixes from automated review were consolidated into one change: live-region copy buttons, `aria-expanded`/`aria-controls` on expandable sections, unique ids, tooltips on icon-only buttons.
- `/analyze` no longer generates a reply it then discards.

### Security

- Safety layer validates outgoing replies and blocks real personal data (US-024).
- API errors are handled without leaking internals; the cheaper fallback model keeps sessions running when the primary model is unavailable (US-022, US-023).

[0.1.0]: https://github.com/lukaszsajkowski/phish-guard-pro/releases/tag/v0.1.0
