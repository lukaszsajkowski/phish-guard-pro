## 2026-08-26 - Dynamic state for icon-only copy buttons
**Learning:** Using a static `aria-label` on an icon-only button that updates its state (e.g. "Copy" -> "Copied!") prevents screen readers from announcing the state change, as the static label overrides inner dynamic content.
**Action:** Remove static `aria-label`s on such buttons. Instead, apply `aria-live="polite"` to the button and include a visually hidden `<span>` (e.g., `className="sr-only"`) whose text updates dynamically to ensure state changes are announced properly.
