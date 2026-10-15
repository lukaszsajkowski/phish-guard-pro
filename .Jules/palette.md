## 2023-10-25 - Accessible Expand/Collapse Toggles
**Learning:** For dynamic expand/collapse buttons, visual cues (like "Show more" or chevron icons) are insufficient for screen readers. They need explicit connection to the content they control and their current state.
**Action:** Always implement `aria-expanded` on the toggle button and link it to the target content container using `aria-controls` with a dynamically generated ID (e.g., via React's `useId()`).
