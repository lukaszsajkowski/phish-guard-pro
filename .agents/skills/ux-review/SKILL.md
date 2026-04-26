---
name: ux-review
description: Run a UX/UI audit on PhishGuard's frontend against cybersecurity dashboard best practices (`/ux-review`, `/ux-review frontend/src/components/app/IntelDashboard.tsx` for scoped audit, `/ux-review history` for a specific area). Use when the user wants to improve the UI, before a design review, or after implementing a new frontend feature. Proposes concrete, actionable changes with severity ratings.
---

# /ux-review — UX/UI audit for cybersecurity dashboard

**Arguments:** `$ARGUMENTS` — optional scope:
- empty → full audit (all pages and components)
- a file or directory path → scoped audit (just that component and its children)
- a feature area name → scoped audit: `chat`, `intel`, `history`, `session`, `auth`, `layout`
- `diff` → audit only frontend files changed since `main` (`git diff --name-only main...HEAD -- frontend/src/`)

## Your job

Audit the PhishGuard Pro frontend against established UX/UI best practices for **cybersecurity dashboards**, **SOC analyst tools**, **threat intelligence platforms**, and **AI agent interfaces**. Produce a prioritized list of concrete, actionable improvements. **You do NOT apply fixes in this skill** — propose changes and delegate implementation if the user approves.

## Context: what PhishGuard Pro is

PhishGuard Pro is an AI-powered Active Defense system against phishing. It engages attackers in believable conversation (tarpitting) and extracts Indicators of Compromise (IOCs). The primary user is a **security analyst** who:
- Pastes phishing emails and monitors AI-generated responses
- Reviews extracted IOCs (BTC wallets, IBANs, URLs, phone numbers, emails)
- Makes human-in-the-loop decisions (continue, edit, end session)
- Exports threat intelligence for SOC/SIEM consumption
- Reviews historical sessions for patterns

The UI must balance **information density** (analyst needs data) with **cognitive load management** (43% higher cognitive load than typical enterprise apps per UX research).

## Cybersecurity UX standards to audit against

### 1. Severity color coding consistency
- Critical=dark red, High=red, Medium=orange, Low=yellow, Info/Clean=green, Unknown=gray
- Same thresholds everywhere (risk score colors must match across `ioc.ts`, `SessionHistoryList`, `RiskScoreBreakdown`, `IntelDashboard`)
- Never rely on color alone — always pair with text labels, icons, or patterns

### 2. Dark mode and contrast
- No pure black backgrounds (use warm-toned near-blacks)
- Desaturated accent colors on dark surfaces
- WCAG AA minimum: 4.5:1 body text, 3:1 large text
- Audit `text-muted-foreground` on `bg-muted/30` stacked transparencies
- Check red/green text on dark backgrounds for color-blind accessibility

### 3. Information density and layout
- Card-based grouping for related data
- Three-tier alert layout: critical top, moderate middle, informational bottom
- Max 5-7 primary widgets per view
- Sticky panels for persistent context (intel panel during chat)
- SOC standard split-panel: conversation left, context/enrichment right

### 4. Progressive disclosure
- Summary first, details on demand (expandable sections)
- Classification reasoning should be collapsible
- Timeline limited to recent N events with "View all" expand
- IOC details behind expand, not all fields shown by default

### 5. AI chat interface and human-in-the-loop
- Visual distinction between actors (bot vs scammer vs system)
- Agent reasoning transparency (thinking panels)
- Multi-step progress indicators for AI pipeline (not just spinner)
- Confidence indicators on AI-generated content
- Edit/undo capabilities for AI outputs
- Turn counter prominence scaling with urgency

### 6. Threat intelligence display
- Defang URLs in display (`hxxps://evil[.]com`) to prevent accidental clicks
- Group IOCs by type (not flat chronological list)
- Sort high-value IOCs to top
- Show confidence scores on IOC cards
- First seen / last seen timestamps
- IOC count summary bar by type

### 7. Risk scoring visualization
- Large prominent score with color-coded progress bar
- Component breakdown with weights
- Trend indicators (up/down/stable arrows)
- Gauge/dial consideration for total score
- CTA for improving data quality (enrich IOCs)

### 8. Data export UX
- Multiple formats (JSON, CSV, STIX 2.1)
- Export preview before download
- Scope control (all vs filtered)
- Disabled states with explanatory tooltips
- Meaningful filenames with session context

### 9. Session history and management
- Filtering by attack type, date range, risk level
- Search by IOC value or persona name
- Session status badges (active/completed/abandoned)
- Relative timestamps with exact dates on hover
- Card view vs table view toggle for power users

### 10. Notifications and feedback
- Toast notifications for successful actions (export, enrichment, copy)
- Inline alerts for contextual errors
- Modal dialogs only for critical decisions
- Never timed dismissal for security alerts
- Activity log / notification center

### 11. Loading and empty states
- Skeleton screens instead of centered spinners
- Informational empty states with next-action CTAs
- Multi-step progress for agent pipeline
- Optimistic updates where safe

### 12. Accessibility
- `aria-label` on all icon-only buttons
- Keyboard navigation on clickable cards (`role="button"`, `tabIndex={0}`)
- `prefers-reduced-motion` support for animations
- `aria-valuenow/min/max` on progress indicators
- Focus management when dialogs open (shadcn/ui handles this)

### 13. Typography
- Monospace (`font-mono`) for all technical data (IOC values, hashes, IPs)
- Minimum `text-sm` (14px) for frequently-read data — avoid `text-xs` overuse
- Uppercase tracking for section labels
- Inter for UI text, JetBrains Mono for technical data

### 14. Micro-interactions
- Entrance animations for new IOCs (fade-in/slide-in)
- Animated risk score transitions (count up/down)
- Pulse effect on new high-value IOC
- Copy-to-clipboard tooltip feedback ("Copied!")
- 150-300ms transitions for hover/state changes

## Steps

1. **Resolve scope** from `$ARGUMENTS`:
   - If empty → audit all pages and components
   - If `diff` → run `git diff --name-only main...HEAD -- frontend/src/` and audit only changed files
   - If feature area → map to component paths:
     - `chat` → `ChatArea`, `ChatMessage`, `ScammerInput`
     - `intel` → `IntelDashboard`, `RiskScoreBreakdown`, IOC-related components
     - `history` → `SessionHistoryList`, `SessionDetailHeader`, `ReadOnlyChatArea`, `Pagination`
     - `session` → `SessionSummary`, `SessionLimitDialog`, `UnmaskingDialog`, `EndSessionDialog`
     - `auth` → login page, register page, `AuthenticatedLayout`
     - `layout` → `AppSidebar`, `AppHeader`, `AuthenticatedLayout`, responsive patterns
   - If file/directory → use directly

2. **Read each component in scope.** For each component, evaluate against ALL 14 standard categories above. Take notes on:
   - What the component does well (brief, 1 line)
   - What violates a standard (specific: line number, current code, what's wrong, which standard)
   - What's missing (what the standard requires that isn't present)

3. **Cross-component checks** (only for full or multi-component audits):
   - Color consistency: grep for risk score color logic across all components, check thresholds match
   - Typography consistency: grep for `text-xs` usage on data-heavy content
   - Loading state consistency: check all loading states use the same pattern
   - Empty state quality: check all empty states have helpful content
   - Accessibility sweep: grep for `onClick` on non-interactive elements without `role` and `tabIndex`

4. **Classify each finding** by severity:
   - **Critical** — Accessibility violation, security UX issue (e.g., clickable malicious URLs), data loss risk
   - **High** — Inconsistency that confuses analysts, missing standard cybersecurity UX pattern, cognitive overload
   - **Medium** — Improvement that would bring the UI closer to SOC dashboard standards
   - **Low** — Polish, micro-interaction enhancement, nice-to-have

5. **Produce the report** in this format:

   ```
   UX/UI Audit Report — PhishGuard Pro
   Scope: <what was audited>
   
   ## Summary
   - Critical: N findings
   - High: N findings
   - Medium: N findings
   - Low: N findings

   ## Critical findings
   ### [C-01] <Title>
   **Component:** `path/to/file.tsx:line`
   **Standard violated:** <which of the 14 standards>
   **Current behavior:** <what happens now>
   **Expected behavior:** <what should happen per the standard>
   **Fix:** <concrete code-level description of the change>

   ## High findings
   ### [H-01] ...

   ## Medium findings
   ### [M-01] ...

   ## Low findings
   ### [L-01] ...

   ## What's done well
   - <brief list of things that already follow best practices>
   ```

6. **Ask the user** which findings to implement. Offer:
   - "Delegate all Critical + High fixes to `nextjs-frontend-dev`?"
   - "Delegate specific finding(s) by ID?"
   - "Export report as markdown?"

   Do not implement any changes without user approval.

## Hard rules

- **Read-only audit.** Never edit frontend code from this skill. Always delegate to `nextjs-frontend-dev`.
- **Be specific.** Every finding must reference a file path and line number. "The colors could be better" is not a finding.
- **Don't flag what works.** If a component follows the standard correctly, mention it in "What's done well" but don't invent issues.
- **Don't suggest redesigns.** Propose incremental improvements within the existing component architecture. The user didn't ask for a rewrite.
- **Prioritize analyst workflow.** Every recommendation must improve the security analyst's ability to do their job — faster threat assessment, fewer missed IOCs, less cognitive load.
- **No scope creep.** Don't audit backend code, API responses, or database schema. This is a frontend UX skill.
- **Don't repeat yourself.** If the same issue (e.g., missing `aria-label`) appears in 5 components, report it once with all affected files listed, not 5 times.

## Communication

- Polish if the user writes in Polish.
- Lead with the summary table. Details second.
- Use the finding ID format (`[C-01]`, `[H-03]`, `[M-07]`) so the user can reference specific findings.
- If the audit is clean (no Critical or High findings), say so clearly and briefly.
