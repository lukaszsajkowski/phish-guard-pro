## 2024-09-12 - Expand/Collapse Accessibility
**Learning:** Custom expand/collapse widgets must use `aria-expanded` to communicate their state and `aria-controls` to link to the content container. Relying purely on visual state changes (like chevrons) leaves screen reader users without context.
**Action:** Always verify that disclosure buttons implement `aria-expanded` and target an `id` using `aria-controls`.
