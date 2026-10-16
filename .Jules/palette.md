## 2024-05-18 - Dynamic Icon-Only Buttons
**Learning:** Static `aria-label` attributes on dynamic icon-only buttons (like copy buttons that turn into checkmarks) prevent screen readers from announcing state changes, overriding dynamic text.
**Action:** Use `aria-live="polite"` on the button, add a visually hidden `<span className="sr-only">` containing the dynamically updating text, and apply `aria-hidden="true"` to visible icons (SVGs) to prevent duplicate announcements.
