## 2024-09-25 - Dynamic Text in Icon Buttons
**Learning:** Static `aria-label` attributes on interactive elements override dynamically changing visible text (like "Copy" -> "Copied!"), preventing screen readers from announcing the state change. Icon-only buttons that change state need a visually hidden span containing the dynamic text, paired with `aria-live="polite"` on the parent button.
**Action:** Never use static `aria-label` on buttons whose text or state changes dynamically. Instead, use `aria-live="polite"` and a visually hidden `<span>` to manage accessible dynamic text.
