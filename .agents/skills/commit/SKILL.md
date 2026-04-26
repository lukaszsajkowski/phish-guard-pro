---
name: commit
description: >-
  Create a git commit with a properly formatted conventional-commit message
  (`/commit`, `/commit push`, `/commit "feat: add X"`, `/commit push "fix: Y"`).
  Use when the user wants to commit staged or unstaged changes. Drafts the
  message from the diff using PhishGuard's commit style (conventional commits,
  optional US-XXX scope, no Co-Authored-By). Optionally pushes after commit.
  Never force-pushes, never amends, never skips hooks.
---

# /commit — Create a conventional-commit and optionally push

**Arguments:** `$ARGUMENTS` — optional, any combination:
- empty → analyze diff, draft message, show for approval, commit on confirm
- `push` → same as above, then push to the current branch's upstream
- `"message"` → use the provided message verbatim (skip drafting)
- `push "message"` → use provided message and push
- `--no-confirm` → skip the approval step for the drafted message (use when you trust the draft; still asks before push)

## Your job

Produce a clean, conventional commit that matches PhishGuard's existing history style, and optionally push. **Never take any destructive git action** (force push, amend, reset, rebase) from this skill. **Never add Co-Authored-By** — the user's history does not use that attribution.

## PhishGuard commit style (reference from git log)

- **Format**: `<type>: <subject>` or `<type>: US-XXX: <subject>` when tied to a user story
- **Types in active use**: `feat`, `fix`, `docs`, `refactor`, `chore`, `test`
- **Subject**: lowercase start (except proper nouns / acronyms), no trailing period, imperative mood, ~70 chars max
- **Body**: usually omitted — only add a body when the "why" isn't obvious from the diff
- **No footer attribution** — no `Co-Authored-By`, no `Signed-off-by` (check the user's existing commits; do not introduce new conventions)

Examples from this repo:
```
feat: US-026: Interface Responsiveness
fix: collapse feature
docs: requirements for IOC enrichment service foundation and related features
refactor: Replace landing page with login page as main route
chore: Remove generated test results and Playwright report files
```

## Steps

### Preflight (always)

1. **Parse `$ARGUMENTS`** into three flags: `push` (bool), `noConfirm` (bool), `explicitMessage` (string | null).

2. **Run in parallel** (four Bash calls in one message):
   - `git status --short` (never use `-uall`, memory issues on large repos)
   - `git diff --staged` — captures what will actually go into the commit if something is already staged
   - `git diff` — captures unstaged changes
   - `git log -5 --oneline` — reconfirm the style convention for this session

3. **Decide what to stage**:
   - If there are staged changes → commit exactly those (do not add more)
   - If nothing is staged but there are unstaged changes → ask the user: "Nothing staged. Stage all modified tracked files with `git add -u`?" Do NOT use `git add -A` or `git add .` — those can sweep in secrets, build artifacts, or `.env` files
   - If there are untracked files the user probably wants included, list them explicitly and ask which to add by name
   - If nothing is staged and nothing unstaged → stop, tell the user "nothing to commit"

4. **Sanity-check for secrets / bad files** — scan the diff (staged + what's about to be staged) for:
   - `.env`, `.env.local`, `credentials`, `*.pem`, `*.key` file paths
   - Literal strings that look like API keys: `sk-`, `SUPABASE_SERVICE_ROLE_KEY=`, `OPENAI_API_KEY=`, long hex/base64 tokens
   - If ANY hit → stop and show the exact file:line, warn the user, ask explicitly whether to include it. Never pass silently.

### Draft message (if no `explicitMessage`)

5. **Analyze the diff** to infer:
   - **Type**: new files + new functions/routes → `feat`; bugfix patterns (ternary flips, null checks, off-by-one, condition reversals) → `fix`; only `*.md` changed → `docs`; only test files changed → `test`; moved/renamed/restructured without behavior change → `refactor`; dependency bumps / tooling / generated files → `chore`
   - **Scope (US-XXX)**: check current branch name (`git branch --show-current`) for a US pattern; check diff for references to specific user stories in comments or imports; if detected and unambiguous, include as `<type>: US-XXX: <subject>`
   - **Subject**: one imperative-mood sentence describing WHAT changed, ~50-70 chars
   - **Body**: only add if the "why" is non-obvious from the diff (e.g. fix for a specific race, workaround for an upstream bug, intentional revert). Otherwise omit — the user's history strongly prefers subject-only.

6. **If `noConfirm` is false**, present the draft:
   ```
   Proposed commit:
     feat: US-033: scaffold IOC enrichment service interface

   Files (3):
     + backend/src/phishguard/services/enrichment_service.py
     M backend/src/phishguard/services/__init__.py
     M backend/tests/unit/services/test_enrichment_service.py

   Confirm? (yes / edit message / cancel)
   ```
   Wait for user response. On `edit`, accept a new message and re-confirm. On `cancel`, stop (leave staging as-is, the user may want to use git directly).

### Commit

7. **Stage what's needed** (if step 3 decided to add):
   - For `git add -u`: run it exactly as agreed
   - For explicit files: `git add <path1> <path2>` — no wildcards

8. **Create the commit** using a HEREDOC to preserve formatting:
   ```
   git commit -m "$(cat <<'EOF'
   <type>: <subject>

   <optional body>
   EOF
   )"
   ```

   **Never** use `-m "msg1" -m "msg2"` style (gets quoting wrong for subjects with quotes). Always HEREDOC.

9. **Check hooks didn't silently block** — run `git status` after the commit. If the commit didn't actually land (pre-commit hook rejected it), the hook failure output is already visible. DO NOT amend or retry with `--no-verify`. Report the hook failure verbatim and ask the user whether to:
   - Fix the underlying issue (preferred — delegate to the right subagent)
   - Skip the hook (only with explicit user request, and warn that this bypasses their safety net)

### Push (only if `push` flag)

10. **Before pushing**, verify:
    - Current branch has an upstream: `git rev-parse --abbrev-ref --symbolic-full-name @{u}` — if no upstream, the skill will set it with `git push -u origin <branch>` on first push, but ASK first
    - We are NOT on `main` / `master` (check `git branch --show-current`). If we are, warn: "You're on main. Push directly to main?" — do not refuse, but require explicit confirmation
    - There are no unpushed commits being overwritten by anything weird (`git log @{u}..HEAD --oneline` to show what will be pushed)

11. **Push**:
    ```
    git push              # if upstream exists and is ahead
    git push -u origin <branch>   # if no upstream, first push
    ```
    **Never** `git push --force`. If the remote rejects the push as non-fast-forward, stop and tell the user — do not "fix" with force.

12. **On push rejection** (non-fast-forward, hook rejection, branch protection): surface the error verbatim. Do not retry with force or `--force-with-lease` without explicit user instruction.

### Final report

13. Single compact block:
    ```
    Committed ✓
      abc1234  feat: US-033: scaffold IOC enrichment service interface

    Pushed ✓                                 ← only if push succeeded
      origin/feature/us-033  →  abc1234
    ```

    On commit without push:
    ```
    Committed ✓
      abc1234  feat: US-033: scaffold IOC enrichment service interface

    Not pushed. Run `/commit push` or `git push` when ready.
    ```

## Hard rules

- **NEVER** use `git add -A` or `git add .` — security risk (sweeps `.env`, secrets, build artifacts)
- **NEVER** use `git commit --amend` — user hasn't asked for it, and amends can silently destroy work when a prior commit already landed
- **NEVER** use `git commit --no-verify` — hooks exist for a reason; if they fail, fix the underlying issue
- **NEVER** use `git push --force` or `--force-with-lease` — wait for explicit instruction
- **NEVER** push to `main` / `master` without explicit confirmation in the same turn
- **NEVER** add `Co-Authored-By: Claude` — user's git history does not use that attribution; do not introduce it
- **NEVER** modify `.gitconfig` or git hooks
- **NEVER** run `git reset --hard`, `git checkout .`, or `git clean -f` from this skill
- **NEVER** commit files flagged in the secrets sanity check (step 4) without explicit user "yes, include it"
- **NEVER** use `git rebase -i` or `git add -i` — interactive mode breaks the skill

## Edge cases

- **Merge conflicts in progress** — if `git status` shows unmerged paths, stop and tell the user to resolve first. Do not try to auto-resolve.
- **Detached HEAD** — stop and tell the user, do not commit on detached HEAD (loses history)
- **Empty commit requested** — do not create empty commits (`--allow-empty`) without explicit user instruction
- **Huge diff** (100+ files) — warn the user and ask whether they really meant to stage everything, often a sign of missing `.gitignore` entry
- **Binary files** — call out large binaries in the file list so the user can reconsider

## Communication

- Polish if the user writes in Polish.
- On success, the final report IS the response. No narration.
- On any stop (missing changes, secrets detected, hook failure, push rejection), lead with "STOPPED: <reason>" then the evidence.
