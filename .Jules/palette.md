## 2024-09-14 - Accessible dynamic text on buttons
**Learning:** For dynamic icon-only buttons (like copy buttons that turn into checkmarks with "Copied!"), using a static \`aria-label\` (e.g. \`aria-label="Copy IOC value"\`) overrides the state change, hiding the feedback from screen readers.
**Action:** Use \`aria-live="polite"\` on the button and include a visually hidden \`<span className="sr-only">\` containing the dynamically updating text (e.g., "Copy to clipboard" -> "Copied!") instead of relying on a static \`aria-label\`.
