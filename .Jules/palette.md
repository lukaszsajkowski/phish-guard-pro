
## 2023-10-25 - Added Tooltips to Icon-Only Buttons
**Learning:** In Radix UI, replacing standard HTML `title` tooltips with Radix `Tooltip` components requires explicitly wrapping the application inside `<TooltipProvider>`, as individual tooltips won't render or share global delays without it. Additionally, testing with RTL/Vitest needs `TooltipProvider` in test wrappers.
**Action:** When adding `Tooltip` to a codebase, ensure `<TooltipProvider>` is added at the root level (e.g. `layout.tsx`) to avoid testing errors and ensure global functionality, and wrap test renders accordingly.
