## 2024-05-24 - Dynamic Copy Button Accessibility
**Learning:** For dynamic icon-only buttons (e.g., copy buttons that change to checkmarks), static `aria-label` attributes hide state changes from screen readers.
**Action:** Remove static `aria-label` attributes, add `aria-live="polite"` to the button, include a visually hidden `<span className="sr-only">` for the dynamically updating text, and add `aria-hidden="true"` to the SVG icons to prevent duplicate announcements.
