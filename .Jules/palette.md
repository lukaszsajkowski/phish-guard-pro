## 2024-05-30 - Dynamic Text in Icon Buttons
**Learning:** Adding a static `aria-label` to a button whose visible inner text changes dynamically (like "Copy" -> "Copied!") overrides the dynamic text, meaning screen readers will not announce the state change.
**Action:** Use `aria-live="polite"` on the button (or container) and ensure the dynamically changing text is accessible (e.g., in a visibly changing span or a `.sr-only` span) instead of a static `aria-label`.
