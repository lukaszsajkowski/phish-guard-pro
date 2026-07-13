## 2024-07-13 - Added Global TooltipProvider
**Learning:** For global tooltip delays to work in Radix UI, a `<TooltipProvider>` must wrap the application layout. Wrapping individual tooltips causes them to lose global state.
**Action:** Always wrap the Next.js `RootLayout` in `<TooltipProvider>` rather than wrapping tooltips inside mapped lists.
