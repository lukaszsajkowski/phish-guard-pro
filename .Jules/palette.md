## 2024-05-24 - Dynamic Text in Accessible Buttons
**Learning:** When using a button whose visible text changes dynamically (e.g., 'Copy to clipboard' to 'Copied!'), a static `aria-label` overrides the text content for screen readers, meaning they never announce the state change.
**Action:** Avoid static `aria-label` attributes on buttons with dynamic text. Instead, use `aria-live="polite"` on the button element to ensure screen readers naturally announce the dynamic text updates.
