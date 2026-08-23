## 2024-05-18 - Avoid Static aria-label on Dynamic Interactive Elements
**Learning:** Adding a static `aria-label` to buttons whose visible text/state dynamically changes (e.g., from "Copy" to "Copied!") overrides the dynamic updates for screen reader users, causing the new state to be ignored.
**Action:** Remove static `aria-label` and `title` attributes on these buttons. Instead, use `aria-live="polite"` on the button element and include a visually hidden `span` (`className="sr-only"`) that dynamically updates the text for icon-only buttons, or rely on the visible dynamic text if present.
