## 2024-10-23 - Dynamic Text in Icon-Only Buttons
**Learning:** Adding a static `aria-label` to an icon-only button that changes its visual state (like a Copy button turning into a checkmark) prevents screen readers from announcing the state change, leading to an inaccessible experience.
**Action:** Remove static `aria-label` attributes on dynamic icon-only buttons. Instead, add `aria-live="polite"` to the button and use a visually hidden `span` (`<span className="sr-only">`) containing the dynamically updating text, while ensuring accompanying visual icons have `aria-hidden="true"`.
