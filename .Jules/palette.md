
## 2024-05-18 - Generating Unique IDs for Accessible Expand/Collapse Panels
**Learning:** Using static strings for `aria-controls` and `id` bindings in expandable panels (like email details or risk breakdowns) causes ID collisions when multiple instances of the component render on the same page. This breaks screen reader behavior as they link to the first matching ID.
**Action:** Use React's `useId()` hook to generate unique IDs dynamically. Apply the generated ID to the content container's `id` property and the toggle button's `aria-controls` property.
