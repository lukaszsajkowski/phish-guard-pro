## 2025-03-01 - Dynamic Accessible Buttons
**Learning:** For dynamic icon-only buttons (like copy buttons that change state), static aria-label attributes override state changes.
**Action:** Use aria-live="polite" on the button and include a visually hidden span containing the dynamically updating text to ensure screen readers announce the state changes.
