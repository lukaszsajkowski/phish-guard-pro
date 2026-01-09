import { test, expect } from '@playwright/test';

/**
 * E2E tests for US-028: View Session History List
 *
 * Tests the session history page functionality including:
 * - Authentication protection
 * - Session list display
 * - Pagination controls
 * - Empty state handling
 * - Navigation to session details
 */

test.describe('Session History Page', () => {
    test.describe('Authentication', () => {
        test('should redirect to /login when not authenticated', async ({ page }) => {
            // Try to access history page directly without authentication
            await page.goto('/history');

            // Should be redirected to login page
            await expect(page).toHaveURL('/login');
        });
    });

    test.describe('Authenticated User', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-history-${timestamp}-${random}@example.com`;
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

        test('should load history page when authenticated', async ({ page }) => {
            // Mock API response for sessions
            await page.route('**/api/v1/sessions*', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: [
                            {
                                session_id: 'session-1',
                                title: null,
                                attack_type: 'nigerian_419',
                                attack_type_display: 'Nigerian 419',
                                persona_name: 'Margaret Thompson',
                                turn_count: 5,
                                created_at: new Date().toISOString(),
                                risk_score: 8,
                                status: 'active',
                            },
                        ],
                        total: 1,
                        page: 1,
                        per_page: 20,
                        total_pages: 1,
                    }),
                });
            });

            // Navigate to history page
            await page.goto('/history');

            // Should display the page heading
            await expect(page.getByRole('heading', { name: 'Session History' })).toBeVisible();
        });

        test('should display sessions list', async ({ page }) => {
            // Mock API response with multiple sessions
            await page.route('**/api/v1/sessions*', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: [
                            {
                                session_id: 'session-1',
                                title: null,
                                attack_type: 'nigerian_419',
                                attack_type_display: 'Nigerian 419',
                                persona_name: 'Margaret Thompson',
                                turn_count: 5,
                                created_at: new Date().toISOString(),
                                risk_score: 8,
                                status: 'active',
                            },
                            {
                                session_id: 'session-2',
                                title: null,
                                attack_type: 'ceo_fraud',
                                attack_type_display: 'CEO Fraud',
                                persona_name: 'Robert Chen',
                                turn_count: 3,
                                created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
                                risk_score: 9,
                                status: 'completed',
                            },
                            {
                                session_id: 'session-3',
                                title: null,
                                attack_type: 'romance_scam',
                                attack_type_display: 'Romance Scam',
                                persona_name: 'Dorothy Miller',
                                turn_count: 10,
                                created_at: new Date(Date.now() - 172800000).toISOString(), // 2 days ago
                                risk_score: 7,
                                status: 'active',
                            },
                        ],
                        total: 3,
                        page: 1,
                        per_page: 20,
                        total_pages: 1,
                    }),
                });
            });

            await page.goto('/history');

            // Wait for session list to load
            await expect(page.getByTestId('session-history-list')).toBeVisible();

            // Verify all sessions are displayed
            await expect(page.getByTestId('session-row-session-1')).toBeVisible();
            await expect(page.getByTestId('session-row-session-2')).toBeVisible();
            await expect(page.getByTestId('session-row-session-3')).toBeVisible();

            // Verify attack types are displayed
            await expect(page.getByText('Nigerian 419')).toBeVisible();
            await expect(page.getByText('CEO Fraud')).toBeVisible();
            await expect(page.getByText('Romance Scam')).toBeVisible();

            // Verify persona names are displayed
            await expect(page.getByText('Margaret Thompson')).toBeVisible();
            await expect(page.getByText('Robert Chen')).toBeVisible();
            await expect(page.getByText('Dorothy Miller')).toBeVisible();
        });

        test('should display empty state when no sessions exist', async ({ page }) => {
            // Mock API response with no sessions
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

            await page.goto('/history');

            // Should show empty state
            await expect(page.getByTestId('empty-state')).toBeVisible();
            await expect(page.getByText('No sessions yet')).toBeVisible();

            // Should have link to dashboard
            const dashboardLink = page.getByRole('link', { name: /Start analyzing/i });
            await expect(dashboardLink).toBeVisible();
            await expect(dashboardLink).toHaveAttribute('href', '/dashboard');
        });

        test('should navigate to dashboard with session param when clicking a session', async ({ page }) => {
            const targetSessionId = 'clickable-session-123';

            // Mock API response
            await page.route('**/api/v1/sessions*', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: [
                            {
                                session_id: targetSessionId,
                                title: null,
                                attack_type: 'crypto_investment',
                                attack_type_display: 'Crypto Investment',
                                persona_name: 'Janet Walsh',
                                turn_count: 7,
                                created_at: new Date().toISOString(),
                                risk_score: 6,
                                status: 'active',
                            },
                        ],
                        total: 1,
                        page: 1,
                        per_page: 20,
                        total_pages: 1,
                    }),
                });
            });

            // Mock restore API for when we navigate to dashboard
            await page.route('**/api/v1/session/*/restore', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        session_id: targetSessionId,
                        status: 'active',
                        attack_type: 'crypto_investment',
                        attack_type_display: 'Crypto Investment',
                        confidence: 85,
                        persona: {
                            persona_type: 'greedy_investor',
                            name: 'Janet Walsh',
                            age: 42,
                            style_description: 'Eager for returns',
                            background: 'Real estate investor',
                        },
                        messages: [],
                        iocs: [],
                        turn_count: 7,
                        turn_limit: 20,
                        is_at_limit: false,
                    }),
                });
            });

            await page.goto('/history');

            // Wait for session to be visible
            await expect(page.getByTestId(`session-row-${targetSessionId}`)).toBeVisible();

            // Click on the session
            await page.getByTestId(`session-row-${targetSessionId}`).click();

            // Should navigate to dashboard with session parameter
            await expect(page).toHaveURL(new RegExp(`/dashboard\\?session=${targetSessionId}`));
        });
    });

    test.describe('Pagination', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-pagination-${timestamp}-${random}@example.com`;
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

        test('should display pagination controls when multiple pages exist', async ({ page }) => {
            // Track current page for API responses
            let currentPage = 1;

            // Mock API response with pagination
            await page.route('**/api/v1/sessions*', async route => {
                const url = new URL(route.request().url());
                const requestedPage = parseInt(url.searchParams.get('page') || '1');
                currentPage = requestedPage;

                // Generate sessions for the requested page
                const sessionsPerPage = 20;
                const totalSessions = 45; // 3 pages total
                const startIdx = (requestedPage - 1) * sessionsPerPage;
                const items = [];

                for (let i = startIdx; i < Math.min(startIdx + sessionsPerPage, totalSessions); i++) {
                    items.push({
                        session_id: `session-${i + 1}`,
                        title: null,
                        attack_type: 'nigerian_419',
                        attack_type_display: 'Nigerian 419',
                        persona_name: `Persona ${i + 1}`,
                        turn_count: i + 1,
                        created_at: new Date(Date.now() - i * 3600000).toISOString(),
                        risk_score: (i % 10) + 1,
                        status: 'active',
                    });
                }

                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items,
                        total: totalSessions,
                        page: requestedPage,
                        per_page: sessionsPerPage,
                        total_pages: 3,
                    }),
                });
            });

            await page.goto('/history');

            // Wait for pagination to be visible
            await expect(page.getByTestId('pagination')).toBeVisible();

            // Verify page numbers are shown
            await expect(page.getByTestId('pagination-page-1')).toBeVisible();
            await expect(page.getByTestId('pagination-page-2')).toBeVisible();
            await expect(page.getByTestId('pagination-page-3')).toBeVisible();

            // Verify prev/next buttons
            await expect(page.getByTestId('pagination-prev')).toBeVisible();
            await expect(page.getByTestId('pagination-next')).toBeVisible();
        });

        test('should have Previous button disabled on first page', async ({ page }) => {
            await page.route('**/api/v1/sessions*', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: Array.from({ length: 20 }, (_, i) => ({
                            session_id: `session-${i + 1}`,
                            title: null,
                            attack_type: 'nigerian_419',
                            attack_type_display: 'Nigerian 419',
                            persona_name: `Persona ${i + 1}`,
                            turn_count: i + 1,
                            created_at: new Date().toISOString(),
                            risk_score: 5,
                            status: 'active',
                        })),
                        total: 40,
                        page: 1,
                        per_page: 20,
                        total_pages: 2,
                    }),
                });
            });

            await page.goto('/history');

            await expect(page.getByTestId('pagination')).toBeVisible();
            await expect(page.getByTestId('pagination-prev')).toBeDisabled();
            await expect(page.getByTestId('pagination-next')).not.toBeDisabled();
        });

        test('should have Next button disabled on last page', async ({ page }) => {
            await page.route('**/api/v1/sessions*', async route => {
                const url = new URL(route.request().url());
                const requestedPage = parseInt(url.searchParams.get('page') || '1');

                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: Array.from({ length: requestedPage === 2 ? 10 : 20 }, (_, i) => ({
                            session_id: `session-page${requestedPage}-${i + 1}`,
                            title: null,
                            attack_type: 'nigerian_419',
                            attack_type_display: 'Nigerian 419',
                            persona_name: `Page${requestedPage} User ${i + 1}`,
                            turn_count: i + 1,
                            created_at: new Date().toISOString(),
                            risk_score: 5,
                            status: 'active',
                        })),
                        total: 30,
                        page: requestedPage,
                        per_page: 20,
                        total_pages: 2,
                    }),
                });
            });

            await page.goto('/history');

            // Wait for pagination and click to go to page 2
            await expect(page.getByTestId('pagination')).toBeVisible();
            await page.getByTestId('pagination-page-2').click();

            // Wait for page 2 to load - check for specific session from page 2
            await expect(page.getByTestId('session-row-session-page2-1')).toBeVisible();

            // Next should be disabled on last page
            await expect(page.getByTestId('pagination-next')).toBeDisabled();
            await expect(page.getByTestId('pagination-prev')).not.toBeDisabled();
        });

        test('should navigate to different pages using pagination controls', async ({ page }) => {
            await page.route('**/api/v1/sessions*', async route => {
                const url = new URL(route.request().url());
                const requestedPage = parseInt(url.searchParams.get('page') || '1');

                // Each page has unique persona names to avoid collision
                const attackTypes = ['nigerian_419', 'ceo_fraud', 'romance_scam'];
                const attackDisplays = ['Nigerian 419', 'CEO Fraud', 'Romance Scam'];

                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: Array.from({ length: 20 }, (_, i) => ({
                            session_id: `session-page${requestedPage}-item${i + 1}`,
                            title: null,
                            attack_type: attackTypes[requestedPage - 1],
                            attack_type_display: attackDisplays[requestedPage - 1],
                            persona_name: `User P${requestedPage}I${i + 1}`,
                            turn_count: i + 1,
                            created_at: new Date().toISOString(),
                            risk_score: 5,
                            status: 'active',
                        })),
                        total: 60,
                        page: requestedPage,
                        per_page: 20,
                        total_pages: 3,
                    }),
                });
            });

            await page.goto('/history');

            // Verify page 1 content - use session testid for reliability
            await expect(page.getByTestId('session-row-session-page1-item1')).toBeVisible();
            await expect(page.getByText('Nigerian 419').first()).toBeVisible();

            // Navigate to page 2
            await page.getByTestId('pagination-page-2').click();

            // Verify page 2 content - use session testid for reliability
            await expect(page.getByTestId('session-row-session-page2-item1')).toBeVisible();
            await expect(page.getByText('CEO Fraud').first()).toBeVisible();

            // Navigate using Next button
            await page.getByTestId('pagination-next').click();

            // Verify we're on page 3
            await expect(page.getByTestId('session-row-session-page3-item1')).toBeVisible();

            // Navigate back using Previous button
            await page.getByTestId('pagination-prev').click();

            // Verify we're back on page 2
            await expect(page.getByTestId('session-row-session-page2-item1')).toBeVisible();
        });

        test('should not show pagination when only one page', async ({ page }) => {
            await page.route('**/api/v1/sessions*', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: Array.from({ length: 5 }, (_, i) => ({
                            session_id: `session-${i + 1}`,
                            title: null,
                            attack_type: 'nigerian_419',
                            attack_type_display: 'Nigerian 419',
                            persona_name: `Persona ${i + 1}`,
                            turn_count: i + 1,
                            created_at: new Date().toISOString(),
                            risk_score: 5,
                            status: 'active',
                        })),
                        total: 5,
                        page: 1,
                        per_page: 20,
                        total_pages: 1,
                    }),
                });
            });

            await page.goto('/history');

            // Session list should be visible
            await expect(page.getByTestId('session-history-list')).toBeVisible();

            // Pagination should not be visible
            await expect(page.getByTestId('pagination')).not.toBeVisible();
        });
    });

    test.describe('Error Handling', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-error-${timestamp}-${random}@example.com`;
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
            // Mock API to return error
            await page.route('**/api/v1/sessions*', async route => {
                await route.fulfill({
                    status: 500,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        error: 'Internal server error',
                    }),
                });
            });

            await page.goto('/history');

            // Should show error message
            await expect(page.getByText('Failed to Load Sessions')).toBeVisible();
        });

        test('should allow retry when API fails', async ({ page }) => {
            let requestCount = 0;

            await page.route('**/api/v1/sessions*', async route => {
                requestCount++;

                if (requestCount === 1) {
                    // First request fails
                    await route.fulfill({
                        status: 500,
                        contentType: 'application/json',
                        body: JSON.stringify({
                            error: 'Internal server error',
                        }),
                    });
                } else {
                    // Subsequent requests succeed
                    await route.fulfill({
                        status: 200,
                        contentType: 'application/json',
                        body: JSON.stringify({
                            items: [
                                {
                                    session_id: 'session-retry-1',
                                    title: null,
                                    attack_type: 'nigerian_419',
                                    attack_type_display: 'Nigerian 419',
                                    persona_name: 'Retry Test',
                                    turn_count: 1,
                                    created_at: new Date().toISOString(),
                                    risk_score: 5,
                                    status: 'active',
                                },
                            ],
                            total: 1,
                            page: 1,
                            per_page: 20,
                            total_pages: 1,
                        }),
                    });
                }
            });

            await page.goto('/history');

            // Should show error initially
            await expect(page.getByText('Failed to Load Sessions')).toBeVisible();

            // Click retry button (uses "Try again" text)
            await page.getByRole('button', { name: /Try again/i }).click();

            // Should now show sessions
            await expect(page.getByTestId('session-row-session-retry-1')).toBeVisible();
            await expect(page.getByText('Retry Test')).toBeVisible();
        });
    });

    test.describe('Risk Score Display', () => {
        test.beforeEach(async ({ page }) => {
            // Register and login flow
            await page.goto('/register');
            const timestamp = Date.now();
            const random = Math.floor(Math.random() * 10000);
            const email = `e2e-test-risk-${timestamp}-${random}@example.com`;
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

        test('should display risk scores with appropriate labels', async ({ page }) => {
            await page.route('**/api/v1/sessions*', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        items: [
                            {
                                session_id: 'session-low-risk',
                                title: null,
                                attack_type: 'nigerian_419',
                                attack_type_display: 'Nigerian 419',
                                persona_name: 'Low Risk Persona',
                                turn_count: 3,
                                created_at: new Date().toISOString(),
                                risk_score: 2,
                                status: 'active',
                            },
                            {
                                session_id: 'session-medium-risk',
                                title: null,
                                attack_type: 'ceo_fraud',
                                attack_type_display: 'CEO Fraud',
                                persona_name: 'Medium Risk Persona',
                                turn_count: 5,
                                created_at: new Date().toISOString(),
                                risk_score: 5,
                                status: 'active',
                            },
                            {
                                session_id: 'session-high-risk',
                                title: null,
                                attack_type: 'crypto_investment',
                                attack_type_display: 'Crypto Investment',
                                persona_name: 'High Risk Persona',
                                turn_count: 8,
                                created_at: new Date().toISOString(),
                                risk_score: 9,
                                status: 'active',
                            },
                        ],
                        total: 3,
                        page: 1,
                        per_page: 20,
                        total_pages: 1,
                    }),
                });
            });

            await page.goto('/history');

            // Verify risk score labels are displayed
            await expect(page.getByText('Low (2/10)')).toBeVisible();
            await expect(page.getByText('Medium (5/10)')).toBeVisible();
            await expect(page.getByText('High (9/10)')).toBeVisible();
        });
    });
});
