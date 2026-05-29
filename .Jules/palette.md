
## 2024-05-29 - [Expand/Collapse ARIA attributes]
**Learning:** For components that toggle the visibility of content (like raw JSON data or details panels), adding `aria-expanded` and `aria-controls` to the trigger button is critical for screen reader users to understand the component's state and relationship to the content.
**Action:** Always pair `aria-expanded` (boolean state) with `aria-controls` (pointing to the ID of the collapsible content container) on buttons that control the visibility of adjacent elements.
