## 2026-07-30 - UseId for Accessibility ID Collisions
**Learning:** Hardcoding accessibility IDs like `aria-controls` in reusable components leads to ID collisions when the component is rendered multiple times on a page, breaking screen reader logic.
**Action:** Use React's `useId()` hook to generate unique, deterministic IDs for elements and ARIA attributes in reusable components to ensure accessibility remains robust.
