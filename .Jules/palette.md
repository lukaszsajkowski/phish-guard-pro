## 2024-05-22 - TooltipProvider Scope
**Learning:** In Radix UI, wrapping every individual `Tooltip` with its own `TooltipProvider` inside a loop or mapped array breaks the global delay feature (so moving from one tooltip to another doesn't instantly show the next one).
**Action:** When mapping over items and adding `Tooltip` components, always ensure that the single `TooltipProvider` wraps the entire list or component, rather than instantiating it per item.
