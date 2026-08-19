## 2024-05-18 - Dynamic Accessible Labels on Copy Buttons
**Learning:** Copy buttons that just change an icon or text need to communicate this state change to screen readers, but removing the primary `aria-label` breaks navigation.
**Action:** Use dynamic `aria-label` values combined with `aria-live="polite"` or ensure visible text acts as the live region so screen readers announce the "Copied!" state without losing the button context.
