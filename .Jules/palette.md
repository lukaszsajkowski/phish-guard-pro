## 2024-05-23 - TooltipProvider usage in React Testing Library
**Learning:** When using Radix UI tooltips in a Next.js app, adding `<TooltipProvider>` to `layout.tsx` enables tooltips globally in the app. However, this does not apply to React Testing Library tests, which render components in isolation. Any test rendering a component with a `<Tooltip>` must wrap it in its own `<TooltipProvider>`, or the test will fail due to the missing context.
**Action:** Always wrap components containing tooltips in `<TooltipProvider>` within test `render` functions.
