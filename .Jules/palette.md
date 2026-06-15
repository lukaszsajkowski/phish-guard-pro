## 2024-06-15 - Tooltip accessibility on icon-only buttons
**Learning:** For enhanced accessibility and user experience, icon-only buttons (like theme toggles) should use both `aria-label` for screen readers and visible `Tooltip`s for sighted mouse/keyboard users.
**Action:** Wrap icon-only buttons in `Tooltip` and `TooltipTrigger asChild`, ensuring `aria-label` is still present on the button. Ensure tests use `TooltipProvider`.
