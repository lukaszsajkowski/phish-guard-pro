## 2026-06-26 - [Dynamic ARIA Controls via useId]
**Learning:** Hardcoding accessibility IDs like 'aria-controls="breakdown-content"' in reusable React components breaks accessibility if the component is used multiple times on a page, causing duplicate DOM IDs.
**Action:** Always use React's 'useId()' hook to generate stable, unique IDs for linked elements (like toggles and their targets) to ensure robust accessibility for screen readers.
