## 2024-11-03 - Accessible Dynamic Copy Buttons
**Learning:** Adding a static `aria-label` to buttons with dynamic content (e.g. Copy -> Copied!) overrides the state change, making it inaccessible to screen readers.
**Action:** Use `aria-live="polite"` on the button, add a visually hidden span containing the dynamic text, and apply `aria-hidden="true"` to the icons to prevent duplicate announcements.
