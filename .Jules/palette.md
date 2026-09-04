## 2024-05-15 - Accessible dynamic button text
**Learning:** Adding static `aria-label` attributes on buttons whose visible inner text changes dynamically (like "Copy" -> "Copied!") overrides the text change, preventing screen readers from announcing it.
**Action:** Remove the static `aria-label` and instead use `aria-live="polite"` on the button. If it is an icon-only button, provide a visually hidden `span` (`<span className="sr-only">`) that updates its content dynamically.
