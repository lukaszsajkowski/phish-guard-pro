## 2024-06-01 - [Add Missing aria-controls to toggle buttons]
**Learning:** [Missing `aria-controls` on expand/collapse toggle buttons breaks the connection between the toggle and its content for screen readers. This is a common pattern in the dashboard code.]
**Action:** [When implementing expandable sections, always verify that the toggle button has `aria-expanded` and `aria-controls` mapped correctly to a unique `id` on the expandable content container.]
