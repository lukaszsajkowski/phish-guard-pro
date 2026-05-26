## 2024-05-18 - [ARIA Controls IDs for Expandable Sections]
**Learning:** When adding accessible IDs for ARIA attributes (like `aria-controls`) in React components, it's essential to use React's `useId()` hook to generate unique IDs. This prevents collisions across multiple instances on the same page.
**Action:** Always use `useId()` when creating components that require paired ID and `aria-controls` properties.
