import { test, expect } from '@playwright/test';

/**
 * E2E tests for US-029: View Session Details
 *
 * Tests the session detail page functionality including:
 * - Authentication protection
 * - Session data display (header, conversation, IOCs, persona)
 * - Read-only mode verification
 * - Error and 404 states
 * - Navigation back to history
 */

test.describe('Session Detail Page', () => {
    const testSessionId = 'test-session-detail-123';

    // Mock session restore response data
    const mockSessionData = {
        session_id: testSessionId,
        status: 'active',
        attack_type: 'nigerian_419',
        attack_type_display: 'Nigerian 419 Scam',
        confidence: 95.5,
        persona: {
            persona_type: 'naive_retiree',
            name: 'Margaret Thompson',
            age: 72,
            style_description: 'Trusting and polite retired teacher',
            background: 'Retired elementary school teacher from Ohio',
        },
        original_email: 'Dear Friend, I am a Nigerian Prince seeking your assistance...',
        messages: [
            {
                id: 'msg-1',
                sender: 'bot',
                content: 'Oh my, this sounds quite interesting! How can I help you?',
                timestamp: new Date().toISOString(),
                thinking: {
                    turn_goal: 'Build rapport with the scammer',
                    selected_tactic: 'Naive curiosity',
                    reasoning: 'Acting as a trusting elderly person who is intrigued by the offer',
                },
            },
            {
                id: 'msg-2',
                sender: 'scammer',
                content: 'I need you to send me $500 via Bitcoin to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                timestamp: new Date(Date.now() - 60000).toISOString(),
            },
            {
                id: 'msg-3',
                sender: 'bot',
                content: 'Oh dear, I am not very familiar with this Bitcoin thing. Can you explain how it works?',
                timestamp: new Date(Date.now() - 30000).toISOString(),
                thinking: {
                    turn_goal: 'Extract more payment information',
                    selected_tactic: 'Confused but willing',
                    reasoning: 'Playing ignorant to get the scammer to reveal more details',
                },
            },
        ],
        iocs: [
            {
                id: 'ioc-1',
                type: 'btc_wallet',
                value: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                is_high_value: true,
                created_at: new Date().toISOString(),
            },
        ],
        turn_count: 3,
        turn_limit: 20,
        is_at_limit: false,
        created_at: new Date().toISOString(),
    };

    test.describe('Authentication', () => {
        test('should redirect to /login when not authenticated', async ({ page }) => {
            // Try to access session detail page directly without authentication
            await page.goto(`/history/${testSessionId}`);

            // Should be redirected to login page (root page is login page in this app)
            await expect(page).toHaveURL(/\/(login)?$/);
        });
    });

    test.describe('Authenticated User', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-detail-${timestamp}-${random}@example.com`;
            const password = 'validPassword123';

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.locator('#confirm-password').fill(password);
            await page.locator('#register-button').click();
            await expect(page.locator('#registration-success-message')).toBeVisible();

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.getByRole('button', { name: 'Sign in' }).click();
            await expect(page).toHaveURL('/dashboard');
        });

        test('should load session detail page when authenticated', async ({ page }) => {
            // Mock session restore API
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Should display session detail header
            await expect(page.getByTestId('session-detail-header')).toBeVisible();
        });

        test('should display conversation history', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Wait for chat area to load
            await expect(page.getByTestId('read-only-chat-area')).toBeVisible();

            // Verify messages are displayed
            await expect(page.getByText('Oh my, this sounds quite interesting!')).toBeVisible();
            await expect(page.getByText(/I need you to send me \$500/)).toBeVisible();
            await expect(page.getByText('Oh dear, I am not very familiar')).toBeVisible();

            // Verify bot and scammer message containers are present
            await expect(page.getByTestId('chat-message-bot').first()).toBeVisible();
            await expect(page.getByTestId('chat-message-scammer')).toBeVisible();
        });

        test('should display Intel Dashboard with IOCs', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Verify Intel Dashboard is displayed
            await expect(page.getByTestId('intel-dashboard')).toBeVisible();

            // Verify attack type section
            await expect(page.getByTestId('attack-type-section')).toBeVisible();
            await expect(page.getByTestId('attack-type-section').getByText('Nigerian 419 Scam')).toBeVisible();

            // Verify confidence badge
            await expect(page.getByTestId('confidence-badge')).toContainText('96%');

            // Verify IOC section
            await expect(page.getByTestId('ioc-section')).toBeVisible();
            await expect(page.getByText('Collected IOCs')).toBeVisible();

            // Verify BTC wallet IOC is displayed
            await expect(page.getByTestId('ioc-item-btc_wallet')).toBeVisible();
            await expect(page.getByTestId('ioc-item-btc_wallet').getByText('bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')).toBeVisible();

            // Verify high value badge
            await expect(page.getByTestId('high-value-badge')).toBeVisible();
        });

        test('should display PersonaCard', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Verify persona card is displayed
            await expect(page.getByTestId('persona-card')).toBeVisible();
            await expect(page.getByText('Margaret Thompson')).toBeVisible();
            await expect(page.getByText('72')).toBeVisible();
            await expect(page.getByText('Trusting and polite retired teacher')).toBeVisible();
        });

        test('should have working Back to history link', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            // Mock history page API
            await page.route('**/api/v1/sessions*', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: [],
                        total: 0,
                        page: 1,
                        per_page: 20,
                        total_pages: 0,
                    }),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Click the back to history link
            const backLink = page.getByTestId('back-to-history-link');
            await expect(backLink).toBeVisible();
            await expect(backLink).toHaveAttribute('href', '/history');

            await backLink.click();

            // Should navigate to history page
            await expect(page).toHaveURL('/history');
        });

        test('should display session metadata in header', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Verify attack type badge
            await expect(page.getByTestId('attack-type-badge')).toContainText('Nigerian 419 Scam');

            // Verify status badge
            await expect(page.getByTestId('status-badge')).toContainText('Active');

            // Verify turn count
            await expect(page.getByTestId('turn-count')).toContainText('3 turns');

            // Verify created date is displayed
            await expect(page.getByTestId('created-at')).toBeVisible();
        });
    });

    test.describe('Read-Only Mode', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-readonly-${timestamp}-${random}@example.com`;
            const password = 'validPassword123';

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.locator('#confirm-password').fill(password);
            await page.locator('#register-button').click();
            await expect(page.locator('#registration-success-message')).toBeVisible();

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.getByRole('button', { name: 'Sign in' }).click();
            await expect(page).toHaveURL('/dashboard');
        });

        test('should not display edit buttons', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Wait for page to load
            await expect(page.getByTestId('read-only-chat-area')).toBeVisible();

            // Verify no edit buttons
            await expect(page.getByTestId('edit-response-button')).not.toBeVisible();
            await expect(page.getByRole('button', { name: /edit/i })).not.toBeVisible();
        });

        test('should not display ScammerInput', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            await expect(page.getByTestId('read-only-chat-area')).toBeVisible();

            // Verify no scammer input
            await expect(page.getByTestId('scammer-input-textarea')).not.toBeVisible();
            await expect(page.getByTestId('scammer-input-send-button')).not.toBeVisible();
        });

        test('should not display Generate Response button', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            await expect(page.getByTestId('read-only-chat-area')).toBeVisible();

            // Verify no generate response button
            await expect(page.getByTestId('generate-response-button')).not.toBeVisible();
        });

        test('should display copy button for bot messages', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Copy button should be visible (this is allowed in read-only mode)
            await expect(page.getByTestId('copy-response-button').first()).toBeVisible();
        });
    });

    test.describe('404 Not Found State', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-notfound-${timestamp}-${random}@example.com`;
            const password = 'validPassword123';

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.locator('#confirm-password').fill(password);
            await page.locator('#register-button').click();
            await expect(page.locator('#registration-success-message')).toBeVisible();

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.getByRole('button', { name: 'Sign in' }).click();
            await expect(page).toHaveURL('/dashboard');
        });

        test('should display 404 state when session not found', async ({ page }) => {
            const nonExistentSessionId = 'non-existent-session-456';

            // Mock API to return 404
            await page.route(`**/api/v1/session/${nonExistentSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 404,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        error: 'Session not found',
                        detail: 'The requested session does not exist',
                    }),
                });
            });

            await page.goto(`/history/${nonExistentSessionId}`);

            // Should show not found message
            await expect(page.getByText('Session Not Found')).toBeVisible();
            await expect(page.getByText(/doesn't exist or you don't have permission/)).toBeVisible();

            // Should have link back to history
            await expect(page.getByRole('link', { name: 'Back to History' })).toBeVisible();
        });

        test('should navigate back to history from 404 page', async ({ page }) => {
            const nonExistentSessionId = 'non-existent-session-789';

            await page.route(`**/api/v1/session/${nonExistentSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 404,
                    contentType: 'application/json',
                    body: JSON.stringify({ error: 'Session not found' }),
                });
            });

            // Mock history page API
            await page.route('**/api/v1/sessions*', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: [],
                        total: 0,
                        page: 1,
                        per_page: 20,
                        total_pages: 0,
                    }),
                });
            });

            await page.goto(`/history/${nonExistentSessionId}`);

            await expect(page.getByText('Session Not Found')).toBeVisible();

            // Click back to history link
            await page.getByRole('link', { name: 'Back to History' }).click();

            await expect(page).toHaveURL('/history');
        });
    });

    test.describe('Error State', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-error-detail-${timestamp}-${random}@example.com`;
            const password = 'validPassword123';

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.locator('#confirm-password').fill(password);
            await page.locator('#register-button').click();
            await expect(page.locator('#registration-success-message')).toBeVisible();

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.getByRole('button', { name: 'Sign in' }).click();
            await expect(page).toHaveURL('/dashboard');
        });

        test('should display error state when API fails', async ({ page }) => {
            const errorSessionId = 'error-session-123';

            // Mock API to return 500 error
            await page.route(`**/api/v1/session/${errorSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 500,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        error: 'Internal server error',
                        detail: 'Database connection failed',
                    }),
                });
            });

            await page.goto(`/history/${errorSessionId}`);

            // Should show error message
            await expect(page.getByText('Failed to Load Session')).toBeVisible();
        });

        test('should allow retry when API fails', async ({ page }) => {
            const retrySessionId = 'retry-session-123';
            let requestCount = 0;

            await page.route(`**/api/v1/session/${retrySessionId}/restore`, async route => {
                requestCount++;

                if (requestCount === 1) {
                    // First request fails
                    await route.fulfill({
                        status: 500,
                        contentType: 'application/json',
                        body: JSON.stringify({ error: 'Internal server error' }),
                    });
                } else {
                    // Subsequent requests succeed
                    await route.fulfill({
                        status: 200,
                        contentType: 'application/json',
                        body: JSON.stringify({
                            ...mockSessionData,
                            session_id: retrySessionId,
                        }),
                    });
                }
            });

            await page.goto(`/history/${retrySessionId}`);

            // Should show error initially
            await expect(page.getByText('Failed to Load Session')).toBeVisible();

            // Click retry button
            await page.getByRole('button', { name: /Try again/i }).click();

            // Should now show session content
            await expect(page.getByTestId('session-detail-header')).toBeVisible();
            await expect(page.getByTestId('read-only-chat-area')).toBeVisible();
        });
    });

    test.describe('Agent Thinking Display', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-thinking-${timestamp}-${random}@example.com`;
            const password = 'validPassword123';

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.locator('#confirm-password').fill(password);
            await page.locator('#register-button').click();
            await expect(page.locator('#registration-success-message')).toBeVisible();

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.getByRole('button', { name: 'Sign in' }).click();
            await expect(page).toHaveURL('/dashboard');
        });

        test('should display thinking panel for bot messages', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Wait for messages to load
            await expect(page.getByTestId('read-only-chat-area')).toBeVisible();

            // Thinking panel should be present for bot messages
            await expect(page.getByTestId('agent-thinking-panel').first()).toBeVisible();
            await expect(page.getByText('Agent Thinking').first()).toBeVisible();
        });

        test('should expand thinking panel to show details', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Click on thinking panel to expand
            const thinkingPanel = page.getByTestId('agent-thinking-panel').first();
            await thinkingPanel.click();

            // Should show thinking details
            await expect(page.getByText('Current Goal').first()).toBeVisible();
            await expect(page.getByText('Build rapport with the scammer')).toBeVisible();
            await expect(page.getByText('Selected Tactic').first()).toBeVisible();
            await expect(page.getByText('Naive curiosity')).toBeVisible();
        });
    });

    test.describe('Timeline Display', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-timeline-${timestamp}-${random}@example.com`;
            const password = 'validPassword123';

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.locator('#confirm-password').fill(password);
            await page.locator('#register-button').click();
            await expect(page.locator('#registration-success-message')).toBeVisible();

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.getByRole('button', { name: 'Sign in' }).click();
            await expect(page).toHaveURL('/dashboard');
        });

        test('should display timeline with IOC extraction events', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Verify timeline section is displayed
            await expect(page.getByTestId('timeline-section')).toBeVisible();
            await expect(page.getByText('Extraction Timeline')).toBeVisible();

            // Should show IOC extraction event (since we have IOCs with created_at)
            await expect(page.getByTestId('timeline-event')).toBeVisible();
        });
    });

    test.describe('Session Without Persona', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-nopersona-${timestamp}-${random}@example.com`;
            const password = 'validPassword123';

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.locator('#confirm-password').fill(password);
            await page.locator('#register-button').click();
            await expect(page.locator('#registration-success-message')).toBeVisible();

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.getByRole('button', { name: 'Sign in' }).click();
            await expect(page).toHaveURL('/dashboard');
        });

        test('should handle session without persona gracefully', async ({ page }) => {
            const sessionWithoutPersona = {
                ...mockSessionData,
                session_id: 'no-persona-session',
                persona: null,
            };

            await page.route('**/api/v1/session/no-persona-session/restore', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(sessionWithoutPersona),
                });
            });

            await page.goto('/history/no-persona-session');

            // Page should still load without errors
            await expect(page.getByTestId('session-detail-header')).toBeVisible();
            await expect(page.getByTestId('read-only-chat-area')).toBeVisible();

            // Persona card should not be visible
            await expect(page.getByTestId('persona-card')).not.toBeVisible();
        });
    });

    test.describe('Session Without Messages', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-nomsg-${timestamp}-${random}@example.com`;
            const password = 'validPassword123';

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.locator('#confirm-password').fill(password);
            await page.locator('#register-button').click();
            await expect(page.locator('#registration-success-message')).toBeVisible();

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.getByRole('button', { name: 'Sign in' }).click();
            await expect(page).toHaveURL('/dashboard');
        });

        test('should show empty state when session has no messages', async ({ page }) => {
            const emptySession = {
                ...mockSessionData,
                session_id: 'empty-session',
                messages: [],
                iocs: [],
                turn_count: 0,
            };

            await page.route('**/api/v1/session/empty-session/restore', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(emptySession),
                });
            });

            await page.goto('/history/empty-session');

            // Should show empty messages state
            await expect(page.getByText('No Messages')).toBeVisible();
            await expect(page.getByText('This session has no conversation history.')).toBeVisible();

            // Header should still be visible
            await expect(page.getByTestId('session-detail-header')).toBeVisible();

            // Intel dashboard should show no IOCs
            await expect(page.getByText('No IOCs extracted yet')).toBeVisible();
        });
    });

    test.describe('Export Functionality (US-030)', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-export-${timestamp}-${random}@example.com`;
            const password = 'validPassword123';

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.locator('#confirm-password').fill(password);
            await page.locator('#register-button').click();
            await expect(page.locator('#registration-success-message')).toBeVisible();

            await page.locator('#email').fill(email);
            await page.locator('#password').fill(password);
            await page.getByRole('button', { name: 'Sign in' }).click();
            await expect(page).toHaveURL('/dashboard');
        });

        test('should display Export JSON button', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Verify export JSON button is visible
            await expect(page.getByTestId('export-json-button')).toBeVisible();
            await expect(page.getByTestId('export-json-button')).toContainText('Export JSON');
        });

        test('should display Export CSV button', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Verify export CSV button is visible
            await expect(page.getByTestId('export-csv-button')).toBeVisible();
            await expect(page.getByTestId('export-csv-button')).toContainText('Export CSV');
        });

        test('should trigger JSON download on Export JSON click', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            // Mock the export endpoint
            await page.route(`**/api/v1/session/${testSessionId}/export/json`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    headers: {
                        'Content-Disposition': 'attachment; filename="phishguard_session.json"',
                    },
                    body: JSON.stringify({ export: 'data' }),
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Set up download listener
            const downloadPromise = page.waitForEvent('download');

            // Click export JSON button
            await page.getByTestId('export-json-button').click();

            // Verify download was triggered
            const download = await downloadPromise;
            expect(download.suggestedFilename()).toContain('phishguard_session');
            expect(download.suggestedFilename()).toContain('.json');
        });

        test('should trigger CSV download on Export CSV click', async ({ page }) => {
            await page.route(`**/api/v1/session/${testSessionId}/restore`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockSessionData),
                });
            });

            // Mock the export endpoint
            await page.route(`**/api/v1/session/${testSessionId}/export/csv`, async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'text/csv',
                    headers: {
                        'Content-Disposition': 'attachment; filename="phishguard_iocs.csv"',
                    },
                    body: 'ioc_type,value\nbtc_wallet,bc1qxy...',
                });
            });

            await page.goto(`/history/${testSessionId}`);

            // Set up download listener
            const downloadPromise = page.waitForEvent('download');

            // Click export CSV button
            await page.getByTestId('export-csv-button').click();

            // Verify download was triggered
            const download = await downloadPromise;
            expect(download.suggestedFilename()).toContain('phishguard_iocs');
            expect(download.suggestedFilename()).toContain('.csv');
        });
    });
});
