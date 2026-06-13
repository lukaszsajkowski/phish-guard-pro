## 2024-03-24 - Act missing in RTL testing
**Learning:** React Testing Library warnings about `act` during setTimeout/async operations in user interaction tests like `fireEvent.click` and timer advances (like `vi.advanceTimersByTimeAsync`) can fail Vitest builds when not properly encapsulated.
**Action:** Always wrap `fireEvent.click` that cause state changes (like showing a "Copied" message) and `vi.advanceTimersByTimeAsync` that trigger state reversions inside `await act(async () => { ... })`.
## 2024-03-24 - Expand/Collapse Accessibility
**Learning:** For accessibility in the frontend, expand/collapse toggle buttons must implement `aria-expanded` and `aria-controls` attributes, and the target content container must have a matching `id`.
**Action:** When creating toggle buttons or expandable sections, always add `aria-expanded={isExpanded}`, `aria-controls="content-id"`, and `id="content-id"` to the target element.
## 2024-03-24 - Unique IDs for ARIA attributes
**Learning:** When adding accessible IDs for ARIA attributes (like `aria-controls`) in React components, use React's `useId()` hook to generate unique IDs and prevent collisions across multiple instances on the same page.
**Action:** Use `const contentId = useId();` instead of hardcoded strings for element IDs that are referenced by ARIA attributes.
