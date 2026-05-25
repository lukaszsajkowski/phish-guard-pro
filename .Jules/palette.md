## 2024-05-25 - [Accessibility] Improve Toggle Button Accessibility with useId

**Learning:** When creating expand/collapse features like in `PhishingEmailCard`, using `aria-expanded` alone is insufficient. Screen readers require an explicit link to the content being toggled using `aria-controls`. Also, React 18's `useId()` is the ideal way to generate a stable, collision-free ID for this `aria-controls` relationship.
**Action:** When implementing expandable content, always pair `aria-expanded` with `aria-controls` on the trigger, and use `useId()` to generate the target container's ID.
