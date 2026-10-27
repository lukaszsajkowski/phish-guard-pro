## 2024-10-27 - Dynamic State Accessibility in Buttons
**Learning:** Static `aria-label` attributes on buttons with dynamic inner text (e.g., "Copy" changing to "Copied!") override the state change, preventing screen readers from announcing the update.
**Action:** Remove static `aria-label` attributes on buttons with dynamic visible text and instead use `aria-live="polite"` to ensure screen readers naturally announce the content changes. Additionally, explicitly hide purely decorative icons with `aria-hidden="true"`.
