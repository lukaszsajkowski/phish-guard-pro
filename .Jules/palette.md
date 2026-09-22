## 2024-05-24 - Accessible dynamic text on copy buttons
**Learning:** Adding static `aria-label` attributes to dynamic buttons (e.g. "Copy to clipboard" -> "Copied!") prevents screen readers from announcing the state change. Instead, use `aria-live="polite"` on the button and a visually hidden `<span>` containing the dynamic text, while hiding the visible icon from screen readers using `aria-hidden="true"`.
**Action:** Use `aria-live=polite` with a visually hidden text element (e.g. `<span className=sr-only>Copied!</span>`) on all copy buttons in the app.
