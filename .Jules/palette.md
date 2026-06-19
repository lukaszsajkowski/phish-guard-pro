## 2026-01-09 - Accessible Icon-Only Buttons
**Learning:** Icon-only or minimally descriptive buttons (like "Edit" and "Copy to clipboard" icons) often miss `aria-label`s. Because these buttons appear repeatedly within lists (like a chat history), ensuring they are explicitly labeled is essential for screen reader users to identify their context and function.
**Action:** When adding or reviewing list items or chat messages containing action buttons (like edit, delete, copy), always verify that an `aria-label` is present to maintain baseline accessibility.
