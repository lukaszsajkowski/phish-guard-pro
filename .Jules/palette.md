## 2024-10-24 - Expand/Collapse Accessibility
**Learning:** Expand/collapse toggle buttons must implement `aria-expanded` and `aria-controls` attributes to be accessible, instead of relying solely on visual cues or text changes (like "Show more").
**Action:** Use React's `useId()` to generate dynamic IDs for the content container and link it to the button's `aria-controls` attribute, ensuring no collisions across multiple instances.
