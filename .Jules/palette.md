## 2023-10-06 - Dynamic Accessible Copy Buttons
**Learning:** Using a static `aria-label` on an icon-only button whose state changes (e.g., Copy -> Copied!) prevents screen readers from announcing the state change.
**Action:** Remove static `aria-label`, add `aria-live="polite"` to the button, and include a visually hidden span (`<span className="sr-only">`) with the dynamic text to ensure state changes are announced. Also use Tooltip for visual feedback.
