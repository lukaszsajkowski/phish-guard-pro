1. **Identify the UX Opportunity:** The `IntelDashboard` component (`frontend/src/components/dashboard/IntelDashboard.tsx`) uses a native `title="Copy to clipboard"` on the copy button for IOCs. According to the "UX Coding Standards", we should use `Tooltip` components instead of native `title` for icon-only buttons for enhanced accessibility and visual polish. I will implement this for the "Copy to clipboard" button, and also check if there are other similar icon-only buttons like "Force refresh (bypass cache)" in the same component.

2. **Add `TooltipProvider` to Root Layout:** I will update `frontend/src/app/layout.tsx` to wrap the children with `TooltipProvider` to ensure tooltips work globally.

3. **Update `IntelDashboard`:**
   - Import `Tooltip`, `TooltipTrigger`, `TooltipContent` from `@/components/ui/tooltip`.
   - Wrap the "Copy to clipboard" `<button>` with `<Tooltip>`.
   - Replace the `title` attribute with `<TooltipContent>`.
   - Do the same for the "Force refresh (bypass cache)" button.

4. **Verify tests and linter:** Run `pnpm lint` and `pnpm test` to ensure I didn't break anything.

5. **Pre-commit steps:** Complete pre commit steps to make sure proper testing, verifications, reviews and reflections are done.

6. **Create PR:** Submit the changes using the provided `submit` tool.
