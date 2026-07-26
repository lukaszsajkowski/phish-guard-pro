## 2024-07-26 - [TooltipProvider]
**Learning:** For enhanced accessibility on the frontend, icon-only buttons should be wrapped in the 'Tooltip' component from '@/components/ui/tooltip' rather than relying solely on native HTML 'title' attributes. <TooltipProvider> must be explicitly added to the root layout (e.g., 'layout.tsx') to enable global delays, and must be included in component test environments (e.g., inside 'render' wrappers) to avoid rendering errors.
**Action:** Always verify TooltipProvider wrap.
