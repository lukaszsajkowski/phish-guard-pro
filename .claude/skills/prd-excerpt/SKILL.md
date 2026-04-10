---
name: prd-excerpt
description: Extract a single user story section from `.ai/prd.md` by ID (e.g. `/prd-excerpt US-033`). Use when the user wants to see the exact PRD text for a specific US without loading the whole document — useful before planning, estimating, or as a quick reference. Read-only.
---

# /prd-excerpt — Extract one US from the PRD

**Arguments:** `$ARGUMENTS` — a user story ID (`US-\d{3}`). Required. If missing or malformed, ask.

## Your job

Print the PRD section for exactly one user story, verbatim. No summary, no interpretation, no code survey. This skill exists to be cheap and deterministic — the opposite of `/us-implement`.

## Steps

1. **Validate** `$ARGUMENTS` matches `US-\d{3}`. If not, ask the user for the correct ID.

2. **Locate the anchor** in `.ai/prd.md` using Grep with pattern `^### US-XXX` (substitute the ID). Capture the line number.

3. **Find the next boundary** — the next `^### US-` heading, or a higher-level heading (`^## `, `^# `), or EOF. Grep for those with line numbers and pick the smallest one greater than the anchor.

4. **Read** that exact line range from `.ai/prd.md` using the Read tool with `offset` and `limit`. Do not read the whole file.

5. **Print the excerpt verbatim** inside a fenced markdown block. Preserve formatting, checkboxes, and the `✅` marker if present. Above the fence, put one line: `PRD excerpt — US-XXX (lines N–M of .ai/prd.md)`.

6. If the US ID is not found, say so and suggest the nearest matches by running Grep for `^### US-` and listing IDs close to the requested one.

## Hard rules

- Never modify `.ai/prd.md`.
- Never summarize or paraphrase — the point is the raw text.
- Do not read the whole PRD. Anchor-and-slice only.

## Communication

- Polish if the user writes in Polish — but the excerpt itself stays in whatever language the PRD uses.
- No preamble beyond the single header line.
