## 2024-05-18 - PhishingEmailCard Accessibility
**Learning:** The expand/collapse toggle for `PhishingEmailCard` lacked proper `aria-expanded` and `aria-controls` attributes, which are essential for screen reader users to understand the state of the component.
**Action:** Always verify that interactive components which control the visibility of other elements have `aria-expanded` properly wired up.
