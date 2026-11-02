## 2024-03-20 - Dynamic Text in Icon Buttons
**Learning:** Adding static aria-labels to buttons where the inner text changes dynamically (like "Copy to clipboard" to "Copied!") overrides the state change, making it inaccessible to screen reader users who only hear the static label.
**Action:** Remove static aria-labels from dynamic buttons. Ensure dynamic text is within an aria-live="polite" region and add visually hidden spans if text needs to be fully accessible without duplicate announcements.
## 2024-03-20 - Expand/Collapse Accessibility
**Learning:** Toggle buttons for expandable content sections that rely only on chevron icons or dynamic aria-labels without aria-expanded/aria-controls lack the proper semantics for screen readers to understand the component's state and relationship.
**Action:** Always add aria-expanded={isExpanded} and an aria-controls attribute pointing to the ID of the expandable content container.
