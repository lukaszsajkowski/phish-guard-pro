## 2026-09-16 - Accessible Dynamic Copy Buttons
**Learning:** Using a static `aria-label` on a button with dynamic text (like "Copy" to "Copied!") overrides the state change for screen readers. Standard test assertions like `toBeInTheDocument()` miss this flaw. Also, icon-only buttons need an `aria-live` region with a visually hidden span for state changes.
**Action:** Always apply `aria-live="polite"` to dynamic action buttons, remove static `aria-labels`, add `aria-hidden="true"` to decorative icons, and explicitly test for `aria-live` attributes.
