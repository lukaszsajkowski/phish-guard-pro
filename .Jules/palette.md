## 2025-01-20 - Adding Tooltips to Icon-Only Buttons
**Learning:** Icon-only buttons should be wrapped in the 'Tooltip' component from '@/components/ui/tooltip' rather than relying solely on native HTML 'title' attributes for enhanced accessibility.
**Action:** When adding accessible IDs or tooltips for icon-only buttons, wrap them with a Radix UI Tooltip and use a global TooltipProvider in the root layout.
