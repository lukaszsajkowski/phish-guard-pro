## 2024-06-08 - Use useId for ARIA Controls in React
**Learning:** When building expand/collapse UI components in React (like "Show Raw Data" toggles inside mapped arrays), explicitly linking the toggle `<button>` and the target `<div id={id}>` using `aria-expanded` and `aria-controls` is required for screen readers. In mapped components, hardcoded IDs will conflict.
**Action:** Use `const id = useId()` or deterministically derived unique IDs (e.g., combining the IOC type/value) to ensure `aria-controls` works perfectly without DOM collisions across the page.
