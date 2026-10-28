## 2024-10-28 - Accessible Expand/Collapse Toggles
**Learning:** Hardcoded chevron SVGs and missing aria attributes on toggles degrade both visual feedback and screen reader experience. Toggles with visible text shouldn't duplicate it in `aria-label`.
**Action:** Use dynamic icons (e.g., `ChevronDown`/`ChevronUp`) based on state, replace redundant `aria-label` with `aria-expanded`, and link to content using `aria-controls` with a matching `id`.
