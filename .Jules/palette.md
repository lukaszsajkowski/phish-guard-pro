
## 2024-05-24 - Global Tooltip Delays with Radix UI
**Learning:** When using Radix UI tooltips, adding `<TooltipProvider>` individually around every icon-only button breaks the global delay feature (where tooltips appear instantly if another tooltip was recently hovered).
**Action:** Always wrap the entire app (e.g., in `layout.tsx`) or at least the parent container in a single `<TooltipProvider>` to preserve global tooltip hover delays, and remember to include the provider in the test environment setup.
