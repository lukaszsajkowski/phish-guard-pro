## 2025-05-05 - Add Tooltips to icon-only buttons
**Learning:** Found multiple icon-only buttons using basic `title` attributes (or just aria-labels) without Tooltips for visual accessibility. Adding `Tooltip` components required `TooltipProvider` at the global level and in tests to avoid rendering errors. Also added tooltips to the ThemeToggle and FallbackModelNotice components.
**Action:** Always wrap `Tooltip` components in `TooltipProvider` in test environments. Add Tooltips to icon-only components instead of relying on `title` attributes.
