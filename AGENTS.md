# AGENTS.md

Rules for coding agents (Claude Code, Gemini, and any other assistant) working in this repository. Project architecture and commands are described in `.claude/CLAUDE.md` and `README.md`.

## What this repo is

PhishGuard Pro is an active-defense system against phishing: LLM agents hold a believable conversation with a scammer, waste their time and extract indicators of compromise. Monorepo: `backend/` (FastAPI + LangGraph), `frontend/` (Next.js), `supabase/` (migrations).

## Workflow

- Never commit to `main`. Work on a branch and open a pull request; `main` is protected and only accepts PRs with green checks.
- Before opening a PR, check that no open PR already covers the same change (`gh pr list`). Extend or replace it instead of opening a duplicate.
- One PR per coherent change. Do not open PRs on a schedule or in bulk.
- A human owner reviews and merges every PR.

## Quality gate (run before every PR)

Backend, from `backend/`:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Frontend, from `frontend/`:

```bash
npx eslint .
npx vitest run
npx tsc --noEmit
```

CI runs the same commands plus `next build`, gitleaks and CodeQL.

## Commits

Conventional commits: `<type>: <subject>` or `<type>: US-XXX: <subject>`; types `feat`, `fix`, `docs`, `refactor`, `chore`, `test`. Imperative, lowercase start, no trailing period. No `Co-Authored-By` or other attribution footers.

## Safety rules

- Never commit `.env` files, API keys or any other secret.
- Never put real personal data (names, emails, phone numbers, IBANs, wallets) into code, fixtures, prompts or test data. Use Faker-generated or clearly fictional values.
- Changes to the safety layer (`backend/src/phishguard/safety/`) or to how the Conversation Agent generates output need a safety review before merge.
