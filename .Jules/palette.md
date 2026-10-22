## 2026-10-22 - Dynamic Icon-Only Button Accessibility
**Learning:** When using dynamic icon-only buttons (like copy buttons that turn into checkmarks), static aria-label attributes fail to announce state changes to screen reader users.
**Action:** Ensure screen readers have context by applying an aria-live="polite" attribute to the button, including a visually hidden span containing the dynamically updating text, and setting aria-hidden="true" on the accompanying visible SVG icons to prevent duplicate announcements.
