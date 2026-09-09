## 2024-09-09 - Dynamic Text Buttons
**Learning:** Adding a static `aria-label` to buttons with dynamically changing inner text (e.g., "Copy to clipboard" -> "Copied!") overrides the state change for screen readers. They will always announce the static label, hiding the update.
**Action:** Remove static `aria-label` from dynamic icon-only buttons. Use `aria-live="polite"` on the button, and ensure visually hidden `<span>` (e.g., `<span className="sr-only">`) is used to wrap the changing text, giving screen readers full context of the state change.
