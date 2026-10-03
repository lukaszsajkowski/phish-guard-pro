## 2024-10-04 - Dynamic Text in Buttons
**Learning:** Screen readers won't announce state changes (like "Copy" changing to "Copied!") if a static `aria-label` is present on the button, as the static label overrides the inner content.
**Action:** When button text updates dynamically, avoid static `aria-label`s. Instead, use `aria-live="polite"` on the button itself and add `aria-hidden="true"` to decorative icons so screen readers announce only the changing text clearly.
