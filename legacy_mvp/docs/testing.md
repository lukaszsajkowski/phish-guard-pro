# PhishGuard Cross-Browser Testing Guide

This document provides testing checklist for verifying PhishGuard UI responsiveness across different browsers (US-024).

## Supported Browsers

- Google Chrome (latest)
- Mozilla Firefox (latest)
- Apple Safari (latest)

## Prerequisites

1. Start the application:
   ```bash
   uv run streamlit run src/phishguard/ui/app.py
   ```

2. Access at `http://localhost:8501`

## Testing Checklist

### 1. Layout Responsiveness

#### At Full Width (1920px+)
- [ ] Main content area displays properly
- [ ] Sidebar shows Intel Dashboard with all sections
- [ ] Chat messages are readable without horizontal scroll
- [ ] Buttons are properly aligned

#### At Minimum Width (1024px)
- [ ] Content doesn't overflow horizontally
- [ ] Text wraps properly in chat messages
- [ ] Buttons don't overlap
- [ ] Sidebar can be collapsed to give more space

#### Sidebar Behavior
- [ ] Sidebar collapse button (arrow) is visible
- [ ] Clicking collapse hides sidebar completely
- [ ] Clicking expand restores sidebar
- [ ] Sidebar width is constrained (250-350px)

### 2. Component Testing

#### Input Stage
- [ ] Email text area is responsive
- [ ] "Analyze Email" button is accessible
- [ ] Demo mode buttons display correctly

#### Analyzing Stage
- [ ] Loading spinner displays properly
- [ ] Error messages (if any) show "Try again" button
- [ ] Error messages don't show stack traces

#### Conversation Stage
- [ ] Chat messages display correctly
- [ ] Bot messages (left) and scammer messages (right) are distinguishable
- [ ] Long URLs wrap properly
- [ ] Edit/Copy buttons are accessible
- [ ] Turn counter displays in sidebar
- [ ] "New session" button appears in header

#### Summary Stage
- [ ] Export buttons work
- [ ] IOC list displays properly
- [ ] Session statistics are readable

### 3. Modal Testing

#### New Session Confirmation (US-023)
- [ ] "New session" button triggers modal
- [ ] Modal displays warning message
- [ ] "Cancel" closes modal without changes
- [ ] "Confirm" resets session and returns to INPUT

#### End Session Confirmation
- [ ] Modal displays properly
- [ ] Buttons are clickable

### 4. Browser-Specific Checks

#### Chrome
- [ ] All CSS styles apply correctly
- [ ] Fonts render properly
- [ ] Animations are smooth

#### Firefox
- [ ] Flexbox layouts work correctly
- [ ] Custom scrollbars display (if any)
- [ ] Form inputs render correctly

#### Safari
- [ ] CSS grid/flexbox works correctly
- [ ] Date/time formatting is correct
- [ ] Download buttons work for exports

## Known Limitations

1. **Minimum Width**: The application enforces a minimum width of 1024px. On smaller screens, horizontal scrolling may be required.

2. **Sidebar State**: Streamlit sidebar collapse state doesn't persist across page refreshes.

3. **Export Downloads**: Browser download behavior varies - some browsers may prompt for location, others download directly.

## Reporting Issues

If you find browser-specific issues:

1. Note the browser name and version
2. Describe the expected vs actual behavior
3. Include a screenshot if possible
4. Create an issue in the project repository
