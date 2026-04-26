---
name: safety-audit
description: Run a full safety layer audit on PhishGuard (`/safety-audit`, or `/safety-audit backend/src/phishguard/agents/conversation.py` for a scoped audit). Use whenever the user touches the safety layer, output validator, unmasking detector, PII regexes, blocklists, Conversation Agent output generation, or asks for a security review before merging. Delegates deep analysis to the `security-safety-engineer` subagent.
---

# /safety-audit — Safety layer audit

**Arguments:** `$ARGUMENTS` — optional scope:
- empty → full audit (all safety-relevant paths)
- a file or directory path → scoped audit (just that target and its callers)
- `diff` → audit only files changed since `main` (`git diff --name-only main...HEAD`)

## Your job

Verify the PhishGuard safety layer still blocks real PII, prompt injection, and unsafe outputs — and that no recent change has weakened the Safety Score. **You do NOT relax any safety checks in this skill; read-only analysis, then delegate fixes if needed.**

## Safety surface area (the canonical targets)

Always include these unless the user scoped the audit narrower:

- `backend/src/phishguard/safety/output_validator.py` — blocks real PII/financial data from outgoing responses
- `backend/src/phishguard/safety/unmasking_detector.py` — detects attempts to unmask the AI
- `backend/src/phishguard/agents/conversation.py` — generates outbound responses (every change here is safety-critical)
- `backend/src/phishguard/agents/intel_collector.py` — regex IOC extraction (flip side: must not leak input PII into storage)
- `backend/tests/**/test_*safety*` and `backend/tests/**/test_output_validator*` — tests that gate the Safety Score

## Steps

1. **Resolve scope** from `$ARGUMENTS`. If `diff`, run `git diff --name-only main...HEAD` and intersect with the safety surface above. Otherwise use the provided path or the full surface.

2. **Static pre-check** (you do this before delegating — cheap signal):
   - Grep for weakening patterns: `# TODO`, `# FIXME`, `# noqa`, `skip`, `xfail` inside the safety surface
   - Grep for new `print`, `logger.info`, or `logger.debug` calls that might log raw user input or PII
   - Check if `output_validator` blocklists / PII regex lists have shrunk vs `main` (use `git diff main -- <file>`)
   - Confirm `pytest` markers for safety tests are not `@pytest.mark.skip`

   If you find anything here, include it verbatim in the delegation prompt — the subagent needs the evidence, not a summary.

3. **Delegate to `security-safety-engineer`** via the Agent tool. The prompt MUST include:
   - The scope (which files, why)
   - The static pre-check findings from step 2 (raw diffs / grep hits)
   - The specific PRD/FR requirements the audit must verify (Safety Score 100%, bidirectional validation: input sanitization + output PII blocking, blocklisted domains, financial data blocking, prompt-injection resistance)
   - A request for: (a) a verdict (PASS / FAIL / PASS-WITH-NOTES), (b) specific line-level findings, (c) concrete fixes if FAIL
   - Explicit instruction: do not propose relaxing any safety check to make tests pass

4. **Run the safety test suite** yourself in parallel with the subagent (or after, if you prefer sequential):
   ```
   cd backend && uv run pytest tests/ -k "safety or output_validator or unmasking" -v
   ```
   Capture pass/fail counts and any new failures.

5. **Consolidate the report**:
   - Verdict (PASS / PASS-WITH-NOTES / FAIL)
   - Test results (X/Y passing)
   - Subagent findings (grouped by severity: critical / high / medium / low)
   - Action items if FAIL

6. **If FAIL**, ask the user whether to delegate the fix to `security-safety-engineer` before you make any changes. Never auto-apply safety-layer changes.

## Hard rules

- Never edit safety code directly from this skill. Delegate or ask.
- Never suggest `# noqa`, skipping tests, or loosening regexes as a fix.
- If the audit surfaces real PII in logs, tests, fixtures, or git history — stop and tell the user immediately before continuing the audit.

## Communication

- Polish if the user writes in Polish.
- Lead with the verdict. Evidence second. Fixes last.
