## 2024-03-15 - Dynamic Icon Button Accessibility
**Learning:** Using a static `aria-label` on dynamic icon-only buttons (like copy buttons that change to a checkmark) prevents screen readers from announcing state changes.
**Action:** When adding or modifying dynamic icon-only buttons, remove static `aria-labels` and use `aria-live="polite"` alongside a visually hidden `<span className="sr-only">` block that contains the dynamically changing text.
