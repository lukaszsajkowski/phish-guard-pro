## 2024-05-18 - Dynamic icon-only buttons
**Learning:** Adding a static `aria-label` to a dynamic icon-only button (e.g. a copy button that turns into a checkmark) prevents screen readers from announcing state changes.
**Action:** Remove static `aria-label`, use `aria-live="polite"`, and conditionally render screen-reader-only text (e.g. `<span className="sr-only">Copied!</span>`) within the button based on state.
