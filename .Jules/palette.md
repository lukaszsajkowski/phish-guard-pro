## 2024-05-24 - Dynamic Copy Button Accessibility
**Learning:** Static `aria-label` overrides dynamic inner text changes (like "Copy" -> "Copied!"). Standard assertions like `getByText` fail or are insufficient for a11y testing.
**Action:** Remove static `aria-label`, add `aria-live="polite"` to the button, and use visually hidden spans (`<span className="sr-only">`) combined with `aria-hidden="true"` on visible elements to ensure screen readers announce state changes correctly. Update tests to use `getAllByText` when text appears in both visible and `sr-only` elements.
