---
name: new-shadcn-component
description: Scaffold a new component in PhishGuard's frontend (e.g. `/new-shadcn-component SessionTimeline`, `/new-shadcn-component ui/badge`). Use when the user wants a new React component. For `ui/*` targets, installs via `npx shadcn@latest add`. For feature components, creates a file in `frontend/src/components/` following the existing project pattern (React 19 + Tailwind CSS v4 + TypeScript).
---

# /new-shadcn-component — Scaffold a frontend component

**Arguments:** `$ARGUMENTS` — the component name in one of two forms:
- `ComponentName` → feature component at `frontend/src/components/ComponentName.tsx`
- `ui/name` → shadcn primitive installed via the shadcn CLI into `frontend/src/components/ui/name.tsx`

Required. If missing or ambiguous, ask.

## Your job

Create a new component that matches PhishGuard's existing frontend conventions: React 19 function components, Tailwind CSS v4 utilities, shadcn/ui primitives, TypeScript strict mode, `cn()` helper from `@/lib/utils`.

## Two modes

### Mode A — shadcn primitive (`ui/name`)

If `$ARGUMENTS` starts with `ui/`, this is a request to install an official shadcn primitive.

1. **Check if it already exists** — Glob `frontend/src/components/ui/<name>.tsx`. If yes, stop and tell the user.
2. **Install via the CLI**:
   ```
   cd frontend && npx shadcn@latest add <name>
   ```
   Do NOT hand-write shadcn primitives — always use the CLI, because it pulls the canonical version that matches the project's `components.json` config.
3. **Verify** — confirm the file exists and run `npx tsc --noEmit` to catch any type conflicts with existing components.
4. **Report** the file path and a one-line usage example.

### Mode B — feature component (bare name)

If `$ARGUMENTS` is a bare PascalCase name, this is a new project-specific component.

1. **Check for existing** — Glob `frontend/src/components/<Name>.tsx` and `frontend/src/components/<name>/**`. If exists, stop.

2. **Read canonical files** (ALWAYS, do not rely on memory) to match current patterns:
   - `frontend/src/components/ui/button.tsx` — current React/TS patterns (function components, `React.ComponentProps`, `cn()`)
   - One existing feature component in `frontend/src/components/` (pick whatever is most recent) — to match import style, prop typing, and file structure
   - `frontend/src/lib/utils.ts` — confirm `cn()` export path
   - `frontend/tsconfig.json` — confirm path alias is `@/*`

3. **Ask the user** (brief, one message) for:
   - Component purpose (one sentence) — goes into the file-level comment ONLY if the user explicitly provides it; otherwise omit comments per CLAUDE.md
   - Client or server component? (default: server unless it needs hooks/events/browser APIs)
   - Key props (name + type + required/optional)
   - Which shadcn/ui primitives it should compose (Button, Card, etc.)

4. **Generate the component** at `frontend/src/components/<Name>.tsx`:
   - `'use client'` directive ONLY if client-side (hooks, events, browser APIs)
   - Import shadcn primitives from `@/components/ui/*`
   - Import `cn` from `@/lib/utils` if combining classNames
   - Define props as a TypeScript `interface` or `type` (match the codebase's prevailing style — Read one example first)
   - Export as named export: `export function <Name>(...)`
   - Use Tailwind CSS v4 utilities. Mobile-first responsive classes.
   - No docstrings/comments unless user asked (per CLAUDE.md rule)

5. **Generate a test stub** at `frontend/src/components/__tests__/<Name>.test.tsx` (match whatever test directory convention the project uses — check with Glob first):
   - Import from `@testing-library/react`
   - One render test that asserts the component mounts with minimal props
   - Follow AAA pattern

6. **Run the frontend gate** scoped to the new files:
   ```
   cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/components/__tests__/<Name>.test.tsx
   ```
   Report pass/fail. The scaffold MUST lint-clean and type-check.

7. **Final report** — file paths with `file_path:line_number` references, the props interface, and a one-line usage example showing how to import and render it.

## Hard rules

- Never hand-write shadcn primitives in Mode A — always use the CLI.
- Never skip the canonical-file read in step 2 — patterns drift as the project evolves (e.g. React 19 `use()` hook, Server Actions, new form hooks) and the skill must match whatever's current.
- Never default to `'use client'` — only add it when the component actually needs client-side features. Unnecessary client components hurt performance.
- Never invent prop types based on the name alone. Ask the user.
- Never add inline comments or docstrings unless the user explicitly asks (CLAUDE.md rule).
- Never create `index.ts` barrel files unless the project already uses them.

## Communication

- Polish if the user writes in Polish.
- Keep the props-gathering question in step 3 tight — one message, not a back-and-forth.
- Report with file_path:line_number so the user can jump straight to the scaffold.
