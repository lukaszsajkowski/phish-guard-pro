## 2024-05-18 - Dynamic IDs and ARIA Controls
**Learning:** Using React's `useId()` for `aria-controls` ensures unique IDs across multiple component instances, preventing collision bugs in repetitive components like RiskBreakdown or Lists. However, hardcoded tests will fail and must be updated to expect dynamic ID matching.
**Action:** Always use `useId()` for ARIA pairings (`aria-describedby`, `aria-labelledby`, `aria-controls`) when components can be rendered multiple times on a page. Remember to adjust tests to match attributes rather than literal strings.
