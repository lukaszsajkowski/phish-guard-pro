## 2024-07-29 - Accessible Expand/Collapse with Dynamic IDs
**Learning:** Hardcoded IDs for ARIA attributes (like `aria-controls` for expand/collapse content) cause collisions when components are reused multiple times on the same page (e.g. lists of emails/logs). This breaks screen reader associations.
**Action:** Use React's `useId()` hook to generate unique identifiers dynamically for related interactive elements (toggle buttons and content wrappers) to ensure accessibility features persist correctly across repeated instances.
