## 2024-05-18 - Dynamically generate IDs for ARIA attributes
**Learning:** When adding `aria-expanded` and `aria-controls` for expand/collapse UI components (like dropdown details or raw data views) in lists or mapped elements, hardcoded IDs are not feasible as they could lead to collisions in React components and screen readers mapping to wrong elements.
**Action:** Use React `useId()` hook to generate unique IDs (`rawDataIdPrefix`) and append loop keys (e.g. `` `${rawDataIdPrefix}-${key}` ``) to create unique, valid linkages between button controllers and content containers.
