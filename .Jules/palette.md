## 2024-08-15 - Expand/collapse widgets require explicit ARIA linking
**Learning:** React state-driven disclosure widgets (like the "Details" and "Show raw data" toggles) lack intrinsic semantics, making their state opaque to screen readers despite visual changes like chevron flips.
**Action:** Always implement `aria-expanded` and `aria-controls` on the toggle button, paired with a dynamically generated `id` (via React's `useId()` hook) on the target content container to ensure accessible state linkage.
