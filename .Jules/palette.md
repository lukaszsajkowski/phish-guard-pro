## 2024-08-12 - Dynamic Action Buttons Accessibility
**Learning:** When adding action buttons that have dynamic text (e.g., changing from "Copy to clipboard" to "Copied!"), providing a static `aria-label` attribute overrides the state change, making it invisible to screen readers.
**Action:** Do not use a static `aria-label` for these buttons. Instead, rely on the visible text inside the button and use `aria-live="polite"` to ensure the screen reader announces the dynamic text changes accurately.
