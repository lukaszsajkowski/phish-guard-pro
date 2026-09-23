## 2024-03-24 - Initial creation

## 2024-03-24 - Accessible Expand/Collapse Toggles
**Learning:** Expand/collapse buttons must implement `aria-expanded` and `aria-controls` attributes linking to the content container's `id`. Visual cues (like chevron changes) are insufficient for screen reader users.
**Action:** Always use `useId()` to dynamically generate matching IDs and apply `aria-expanded` state to any toggle buttons controlling visibility of content.
