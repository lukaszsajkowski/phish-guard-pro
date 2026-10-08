## 2024-10-08 - Dynamic Text Buttons Need aria-live, not aria-label
**Learning:** When a button's visible text changes dynamically (e.g., from "Copy to clipboard" to "Copied!"), adding a static `aria-label` prevents screen readers from announcing the state change.
**Action:** Remove static `aria-label`s on buttons with dynamic text. Instead, apply `aria-live="polite"` to the button element so screen readers announce the text change naturally, and add `aria-hidden="true"` to accompanying SVGs and visible text to prevent duplicate announcements.
