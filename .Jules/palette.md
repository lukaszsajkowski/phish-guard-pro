## 2025-01-20 - Ensure icon-only buttons have dynamic aria-live labels for changing states
**Learning:** Using a static aria-label on an icon-only button prevents screen readers from announcing dynamic state changes (e.g. "Copy" changing to "Copied!").
**Action:** Remove static aria-labels. Apply aria-live="polite" to the button and include a visually hidden span containing the dynamically updating text to ensure screen readers receive state updates.
