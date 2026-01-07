import { test, expect } from '@playwright/test';

test.describe('Session Features (US-013, US-014, US-015, US-025)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login (using unique email)
        await page.goto('/register');
        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-session-${timestamp}-${random}@example.com`;
        const password = 'validPassword123';

        await page.locator('#email').fill(email);
        await page.locator('#password').fill(password);
        await page.locator('#confirm-password').fill(password);
        await page.locator('#register-button').click();
        await expect(page.locator('#registration-success-message')).toBeVisible();

        // Login
        await page.locator('#email').fill(email);
        await page.locator('#password').fill(password);
        await page.getByRole('button', { name: 'Sign in' }).click();
        await expect(page).toHaveURL('/dashboard');

        // Mock initial classification
        await page.route('**/api/v1/classification/analyze', async (route) => {
            await route.fulfill({
                status: 200,
                body: JSON.stringify({
                    session_id: 'test-session-id',
                    attack_type: 'ceo_fraud',
                    confidence: 0.95,
                    reasoning: 'Test reasoning',
                    persona: {
                        persona_type: 'skeptical_retiree',
                        name: 'Test Persona',
                        age: 65,
                        style_description: 'Cautious',
                        background: 'Retired',
                    },
                }),
            });
        });

        // Navigate to dashboard and perform initial setup
        // Note: Login already takes us to /dashboard, but we need to ensure we're ready
        await page.getByPlaceholder('Paste phishing email content here...').fill('Test phishing email');
        await page.getByRole('button', { name: 'Analyze', exact: true }).click();
    });

    test('US-013 and US-014: Visualizes Agent Thinking and counts turns', async ({ page }) => {
        // Mock response generation for turn 1
        await page.route('**/api/v1/response/generate', async (route) => {
            await route.fulfill({
                status: 200,
                body: JSON.stringify({
                    content: 'This is a test response.',
                    generation_time_ms: 1000,
                    safety_validated: true,
                    thinking: {
                        turn_goal: 'Test goal',
                        selected_tactic: 'Ask Questions',
                        reasoning: 'Test reasoning',
                    },
                    message_id: 'msg-1',
                    turn_count: 1,
                    turn_limit: 20,
                    is_at_limit: false,
                }),
            });
        });

        // Generate first response
        await page.getByTestId('generate-response-button').click();

        // specific check: turn counter should be "Turn 1/20"
        await expect(page.getByTestId('turn-counter')).toHaveText('Turn 1/20');

        // specific check: agent thinking panel
        const thinkingPanel = page.getByTestId('agent-thinking-panel');
        await expect(thinkingPanel).toBeVisible();
        await expect(thinkingPanel).toHaveText(/Agent Thinking/);

        // Open thinking panel details
        await thinkingPanel.click();
        await expect(thinkingPanel).toHaveText(/Test goal/);
        await expect(thinkingPanel).toHaveText(/Ask Questions/);
        await expect(thinkingPanel).toHaveText(/Test reasoning/);
    });

    test('US-015: Handles session limit warning', async ({ page }) => {
        // Mock response generation forcing turn 20
        await page.route('**/api/v1/response/generate', async (route) => {
            await route.fulfill({
                status: 200,
                body: JSON.stringify({
                    content: 'Response at limit.',
                    generation_time_ms: 1000,
                    thinking: { turn_goal: 'End', selected_tactic: 'Trust', reasoning: 'End' },
                    message_id: 'msg-20',
                    turn_count: 20,
                    turn_limit: 20,
                    is_at_limit: true,
                }),
            });
        });

        await page.getByTestId('generate-response-button').click();

        // Verify dialog appears
        await expect(page.getByRole('alertdialog')).toBeVisible();
        await expect(page.getByText('Session Limit Reached')).toBeVisible();
        await expect(page.getByText("You've reached 20 turns")).toBeVisible();

        // Verify turn counter is red (styling check handled via class check if we want, or loose visual check)
        await expect(page.getByTestId('turn-counter')).toHaveClass(/text-red-500/);

        // Mock extend session
        await page.route('**/api/v1/response/session/test-session-id/extend', async (route) => {
            await route.fulfill({
                status: 200,
                body: JSON.stringify({
                    session_id: 'test-session-id',
                    new_limit: 30,
                    turn_count: 20,
                }),
            });
        });

        // Click Continue
        await page.getByTestId('continue-session-button').click();

        // Dialog should close
        await expect(page.getByRole('alertdialog')).not.toBeVisible();

        // Turn counter should update limit
        // Note: The mocked component state will need to reflect the update. 
        // Since our mock response above hardcoded turn_count: 20, we expect "Turn 20/30" after extension.
        await expect(page.getByTestId('turn-counter')).toHaveText('Turn 20/30');
    });

    test('US-025: Start New Session button resets application state', async ({ page }) => {
        // Mock response generation to active session
        await page.route('**/api/v1/response/generate', async (route) => {
            await route.fulfill({
                status: 200,
                body: JSON.stringify({
                    content: 'Response text',
                    generation_time_ms: 1000,
                    thinking: { turn_goal: 'Goal', selected_tactic: 'Tactic', reasoning: 'Reason' },
                    message_id: 'msg-1',
                    turn_count: 1,
                    turn_limit: 20,
                    is_at_limit: false,
                }),
            });
        });

        // Start session
        await page.getByTestId('generate-response-button').click();

        // Verify "New Session" button is visible in header
        const newSessionBtn = page.getByTestId('new-session-header-button');
        await expect(newSessionBtn).toBeVisible();

        // Click it
        await newSessionBtn.click();

        // Verify confirmation dialog
        const dialog = page.getByTestId('new-session-dialog');
        await expect(dialog).toBeVisible();
        await expect(page.getByText('Start New Session?')).toBeVisible();

        // Test Cancel action
        await page.getByTestId('new-session-cancel-button').click();
        await expect(dialog).not.toBeVisible();
        // Session should be preserved (turn counter still visible)
        await expect(page.getByTestId('turn-counter')).toBeVisible();

        // Test Confirm action
        await newSessionBtn.click();
        await page.getByTestId('new-session-confirm-button').click();

        // Verify reset state
        await expect(dialog).not.toBeVisible();
        // Input should be empty and visible
        const input = page.getByPlaceholder('Paste phishing email content here...');
        await expect(input).toBeVisible();
        await expect(input).toBeEmpty();
        // Chat elements should be gone
        await expect(page.getByTestId('turn-counter')).not.toBeVisible();
    });
});
