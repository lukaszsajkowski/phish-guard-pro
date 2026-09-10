## 2024-05-24 - Dynamic Copy Button Accessibility
**Learning:** Using a static `aria-label` on buttons whose inner text changes dynamically (like "Copy" -> "Copied!") is bad for accessibility because it overrides the visible text change, preventing screen readers from announcing the new state.
**Action:** Remove static `aria-label` attributes from buttons with dynamic state changes. Instead, use `aria-live="polite"` on the button element (and include a visually hidden text span if the button is icon-only) to ensure screen readers announce the state change correctly.
