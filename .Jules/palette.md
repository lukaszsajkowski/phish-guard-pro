
## 2026-06-02 - [Tooltip Accessibility on Icon-only Buttons]
**Learning:** Native `title` attributes on buttons (like those used for expanding/collapsing side panels) or invisible `aria-label`s are not sufficient or always easily discoverable for sighted mouse users. Using custom UI tooltips (like Radix UI's `Tooltip`) is preferred. However, adding `Tooltip` directly into components can crash tests if `TooltipProvider` isn't globally available or appropriately added to test wrappers.
**Action:** Always wrap `children` in `layout.tsx` (and component test wrappers) with a global `TooltipProvider` to enable easy, bug-free usage of Tooltips for icon-only buttons across the Next.js app.
