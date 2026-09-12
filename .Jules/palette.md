## 2024-09-12 - Dynamic Icon-Only Button Accessibility
**Learning:** For dynamic icon-only buttons (like a copy button that changes to a checkmark), using a static `aria-label` prevents screen readers from announcing state changes.
**Action:** Remove the static `aria-label`, add `aria-live="polite"` to the button, and include a visually hidden `<span className="sr-only">` that contains the dynamically updating text (e.g., "Copy" -> "Copied"). Ensure visible icons have `aria-hidden="true"`.
