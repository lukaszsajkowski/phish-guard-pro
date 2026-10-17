## 2024-05-17 - Dynamic Accessibility for Copy Buttons
**Learning:** For dynamic icon-only buttons (like a copy button that changes to a checkmark), static `aria-label` attributes prevent screen readers from announcing the state change ("Copied!").
**Action:** Remove static `aria-label` and replace it with `aria-live="polite"` on the button. Use a visually hidden `<span className="sr-only">` that changes its text dynamically, and ensure icons have `aria-hidden="true"` to prevent duplicate announcements.
