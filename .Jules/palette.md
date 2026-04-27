## 2024-04-27 - [A11y Tooltip Enhancement]
**Learning:** While native HTML `aria-label` attributes provide accessibility for screen readers, they do not provide visual feedback for mouse or keyboard users. For icon-only buttons, pairing an `aria-label` with a visual `Tooltip` component (e.g., Radix UI Tooltip) creates a more universally accessible and discoverable UX pattern.
**Action:** When adding or updating icon-only buttons, supplement `aria-label`s with visual tooltips to provide clear affordances to all users.
