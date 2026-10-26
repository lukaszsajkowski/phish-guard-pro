## 2024-10-26 - Dynamic Text for Icon-only Buttons
**Learning:** Using a static `aria-label` on an icon-only button that changes state (e.g., Copy -> Checkmark) overrides the dynamic state for screen readers.
**Action:** Remove static `aria-label`, add `aria-live="polite"`, and use dynamic visually hidden `<span className="sr-only">` elements alongside `aria-hidden="true"` on the icons to ensure screen readers announce the state change correctly.
