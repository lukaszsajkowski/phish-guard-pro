## 2024-05-24 - Expand/Collapse Toggles in Dynamic Lists
**Learning:** Buttons within dynamic lists or dashboards that toggle additional content (like 'Details' or 'Show raw data') need 'aria-expanded' to accurately convey their current state, and ideally 'aria-controls' to point to the content being toggled, avoiding ambiguity for screen reader users.
**Action:** Always include 'aria-expanded' based on the expanded state, and use 'aria-controls' pointing to a dynamically generated ID when creating expand/collapse functionality, even for small details.
