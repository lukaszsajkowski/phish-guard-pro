import { test, expect } from '@playwright/test';

/**
 * E2E tests for API Error Handling (US-022).
 * 
 * Tests verify:
 * - Error message displayed when API fails
 * - "Try again" button triggers new request
 * - Session state preserved after error
 * - Success after retry works correctly
 */

// Test user credentials
const TEST_USER = {
    email: 'test-error-handling@example.com',
    password: 'TestPassword123!',
};

test.describe('API Error Handling (US-022)', () => {
    test.beforeEach(async ({ page }) => {
        // Login before each test
        await page.goto('/login');
        await page.fill('input[name="email"]', TEST_USER.email);
        await page.fill('input[name="password"]', TEST_USER.password);
        await page.click('button[type="submit"]');
        await page.waitForURL('/dashboard');
    });

    test('displays error message when analysis API fails', async ({ page }) => {
        // Arrange: Mock API to return 503 error
        await page.route('**/api/v1/classification/analyze', route => {
            route.fulfill({
                status: 503,
                contentType: 'application/json',
                body: JSON.stringify({
                    error: 'Unable to connect to the AI service. Please try again.',
                    error_code: 'SERVICE_UNAVAILABLE',
                    should_retry: true,
                }),
            });
        });

        // Act: Submit an email for analysis
        const testEmail = 'Dear Winner, You have won $1,000,000 in our lottery!';
        await page.fill('[data-testid="email-input"]', testEmail);
        await page.click('[data-testid="analyze-button"]');

        // Assert: Error message is displayed
        await expect(page.locator('[data-testid="analysis-error"]')).toBeVisible();
        await expect(page.locator('[data-testid="analysis-error-message"]')).toContainText(
            'Unable to connect to the AI service'
        );

        // Assert: Retry button is available
        await expect(page.locator('[data-testid="analysis-error-retry-button"]')).toBeVisible();
    });

    test('try again button triggers new request for analysis', async ({ page }) => {
        let requestCount = 0;

        // Arrange: First request fails, second succeeds
        await page.route('**/api/v1/classification/analyze', route => {
            requestCount++;
            if (requestCount === 1) {
                route.fulfill({
                    status: 503,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        error: 'Service temporarily unavailable',
                        error_code: 'SERVICE_UNAVAILABLE',
                        should_retry: true,
                    }),
                });
            } else {
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        session_id: 'test-session-123',
                        attack_type: 'lottery_scam',
                        confidence: 92,
                        reasoning: 'Classic lottery scam pattern detected',
                        persona: {
                            name: 'Test User',
                            persona_type: 'naive_retiree',
                            age: 65,
                            style_description: 'Trusting and eager',
                            background: 'Recently retired teacher',
                        },
                    }),
                });
            }
        });

        // Act: Submit email and wait for error
        const testEmail = 'Congratulations! You won our lottery!';
        await page.fill('[data-testid="email-input"]', testEmail);
        await page.click('[data-testid="analyze-button"]');
        await expect(page.locator('[data-testid="analysis-error"]')).toBeVisible();

        // Act: Click retry button
        await page.click('[data-testid="analysis-error-retry-button"]');

        // Assert: Error disappears and classification result shows
        await expect(page.locator('[data-testid="analysis-error"]')).not.toBeVisible();
        await expect(page.locator('[data-testid="classification-result"]')).toBeVisible();
        expect(requestCount).toBe(2);
    });

    test('email content is preserved after analysis error', async ({ page }) => {
        // Arrange: Mock API to return error
        await page.route('**/api/v1/classification/analyze', route => {
            route.fulfill({
                status: 500,
                contentType: 'application/json',
                body: JSON.stringify({
                    error: 'Internal server error',
                    error_code: 'INTERNAL_ERROR',
                    should_retry: true,
                }),
            });
        });

        // Act: Enter email and submit
        const testEmail = 'Important email content that should not be lost';
        await page.fill('[data-testid="email-input"]', testEmail);
        await page.click('[data-testid="analyze-button"]');

        // Wait for error
        await expect(page.locator('[data-testid="analysis-error"]')).toBeVisible();

        // Assert: Email content is still present
        const inputValue = await page.locator('[data-testid="email-input"]').inputValue();
        expect(inputValue).toBe(testEmail);
    });

    test('displays error for response generation failure', async ({ page }) => {
        // Arrange: Mock successful analysis, then failed response generation
        await page.route('**/api/v1/classification/analyze', route => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: 'test-session-456',
                    attack_type: 'ceo_fraud',
                    confidence: 88,
                    reasoning: 'CEO fraud pattern detected',
                    persona: {
                        name: 'John Doe',
                        persona_type: 'stressed_manager',
                        age: 45,
                        style_description: 'Busy and distracted',
                        background: 'IT Manager',
                    },
                }),
            });
        });

        await page.route('**/api/v1/response/generate', route => {
            route.fulfill({
                status: 503,
                contentType: 'application/json',
                body: JSON.stringify({
                    error: 'AI service is temporarily unavailable',
                    error_code: 'SERVICE_UNAVAILABLE',
                    should_retry: true,
                }),
            });
        });

        // Act: Analyze email successfully
        await page.fill('[data-testid="email-input"]', 'Urgent wire transfer needed immediately!');
        await page.click('[data-testid="analyze-button"]');
        await expect(page.locator('[data-testid="classification-result"]')).toBeVisible();

        // Act: Generate response (will fail)
        await page.click('[data-testid="generate-response-button"]');

        // Assert: Generation error is displayed
        await expect(page.locator('[data-testid="generation-error"]')).toBeVisible();
        await expect(page.locator('[data-testid="generation-error-message"]')).toContainText(
            'AI service is temporarily unavailable'
        );
    });

    test('rate limit error shows appropriate message', async ({ page }) => {
        // Arrange: Mock API to return 429 rate limit
        await page.route('**/api/v1/classification/analyze', route => {
            route.fulfill({
                status: 429,
                contentType: 'application/json',
                headers: { 'Retry-After': '30' },
                body: JSON.stringify({
                    error: 'The AI service is currently busy. Please try again in a moment.',
                    error_code: 'RATE_LIMIT',
                    retry_after: 30,
                    should_retry: true,
                }),
            });
        });

        // Act: Submit email
        await page.fill('[data-testid="email-input"]', 'Test email content');
        await page.click('[data-testid="analyze-button"]');

        // Assert: Rate limit error message is shown
        await expect(page.locator('[data-testid="analysis-error"]')).toBeVisible();
        await expect(page.locator('[data-testid="analysis-error-message"]')).toContainText('busy');
    });

    test('session state preserved after generation error', async ({ page }) => {
        // Arrange: Set up successful analysis, then failed generation, then successful generation
        let generateCallCount = 0;

        await page.route('**/api/v1/classification/analyze', route => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: 'test-session-789',
                    attack_type: 'nigerian_419',
                    confidence: 95,
                    reasoning: 'Nigerian 419 scam detected',
                    persona: {
                        name: 'Jane Smith',
                        persona_type: 'greedy_investor',
                        age: 55,
                        style_description: 'Looking for opportunities',
                        background: 'Former accountant',
                    },
                }),
            });
        });

        await page.route('**/api/v1/response/generate', route => {
            generateCallCount++;
            if (generateCallCount === 1) {
                route.fulfill({
                    status: 503,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        error: 'Service unavailable',
                        error_code: 'SERVICE_UNAVAILABLE',
                        should_retry: true,
                    }),
                });
            } else {
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        message_id: 'msg-123',
                        content: 'Dear kind sir, I am very interested in your proposal...',
                        generation_time_ms: 2500,
                        safety_validated: true,
                        turn_count: 1,
                        turn_limit: 20,
                        is_at_limit: false,
                    }),
                });
            }
        });

        // Act: Complete analysis
        await page.fill('[data-testid="email-input"]', 'Dear friend, I am a prince...');
        await page.click('[data-testid="analyze-button"]');
        await expect(page.locator('[data-testid="classification-result"]')).toBeVisible();

        // Store classification result text
        const classificationText = await page.locator('[data-testid="classification-result"]').textContent();

        // Act: First generation fails
        await page.click('[data-testid="generate-response-button"]');
        await expect(page.locator('[data-testid="generation-error"]')).toBeVisible();

        // Assert: Classification result still visible (session preserved)
        await expect(page.locator('[data-testid="classification-result"]')).toBeVisible();
        const classificationTextAfterError = await page.locator('[data-testid="classification-result"]').textContent();
        expect(classificationTextAfterError).toBe(classificationText);

        // Act: Retry generation succeeds
        await page.click('[data-testid="generation-error-retry-button"]');

        // Assert: Error disappears and chat message appears
        await expect(page.locator('[data-testid="generation-error"]')).not.toBeVisible();
        await expect(page.locator('[data-testid="chat-message"]')).toBeVisible();
    });
});
