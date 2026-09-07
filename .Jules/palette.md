## 2024-10-24 - Dynamic Icon Button Accessibility
**Learning:** Using a static `aria-label` on dynamic icon-only buttons (like a copy button that turns into a checkmark) prevents screen readers from announcing state changes.
**Action:** For buttons with dynamic states, avoid static `aria-label` attributes. Instead, use `aria-live="polite"` on the button and include a visually hidden span (`<span className="sr-only">`) with the dynamically updating text.
