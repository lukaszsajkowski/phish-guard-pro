## 2024-05-18 - Tooltip Context for Tests
**Learning:** When using Radix UI `Tooltip` components in Next.js applications, they strictly require a `TooltipProvider` context. If `Tooltip` components are added to an existing UI component, any unit tests rendering that component must be updated to wrap the render target in `<TooltipProvider>`. Otherwise, tests will fail with a context error.
**Action:** Always wrap test renders in `<TooltipProvider>` when adding new tooltip components to existing UI elements.
