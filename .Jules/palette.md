## 2026-08-03 - Accessible Icon-Only Buttons
**Learning:** Native `title` attributes on icon-only buttons are inconsistent across screen readers and often unstyled, causing poor UX. Radix UI Tooltips provide a much better, accessible, and delay-controllable alternative.
**Action:** Replace native `title` attributes with Radix UI `Tooltip` components (using `TooltipTrigger asChild`) for all icon-only buttons to ensure styled visual cues and robust accessibility.
