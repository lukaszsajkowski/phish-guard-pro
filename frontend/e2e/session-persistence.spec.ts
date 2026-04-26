import { test, expect } from '@playwright/test';
import { waitForAnalysisResult } from './helpers/dashboard';

test.describe('Session Persistence on Page Refresh (US-031)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-persistence-${timestamp}-${random}@example.com`;
        const password = 'validPassword123';

        await page.locator('#email').fill(email);
        await page.locator('#password').fill(password);
        await page.locator('#confirm-password').fill(password);

        const registerButton = page.locator('#register-button');
        await expect(registerButton).toBeEnabled();
        await registerButton.click();

        await expect(page.locator('#registration-success-message')).toBeVisible();

        // Login
        await page.locator('#email').fill(email);
        await page.locator('#password').fill(password);
        await page.getByRole('button', { name: 'Sign in' }).click();

        await expect(page).toHaveURL('/dashboard');
    });

    test('should store session ID in URL after analysis', async ({ page }) => {
        const sessionId = 'test-session-url-123';

        // Mock the classification API
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95.5,
                    reasoning: 'Classic 419 indicators detected',
                    classification_time_ms: 500,
                    session_id: sessionId,
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'Margaret Thompson',
                        age: 72,
                        style_description: 'Trusting and polite',
                        background: 'Retired teacher'
                    }
                })
            });
        });

        // Input email content and analyze
        await page.getByTestId('email-input-textarea').fill('Dear Friend, I am a Nigerian Prince...');
        await page.getByTestId('analyze-button').click();

        // Wait for classification to complete
        await waitForAnalysisResult(page);

        // Verify session ID is in URL
        await expect(page).toHaveURL(new RegExp(`session=${sessionId}`));
    });

    test('should restore session state after page refresh', async ({ page }) => {
        const sessionId = 'test-session-refresh-456';

        // Mock the classification API
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'crypto_investment',
                    confidence: 88,
                    reasoning: 'Crypto scam detected',
                    classification_time_ms: 400,
                    session_id: sessionId,
                    persona: {
                        persona_type: 'greedy_investor',
                        name: 'Robert Chen',
                        age: 45,
                        style_description: 'Eager and quick to act',
                        background: 'Day trader'
                    }
                })
            });
        });

        // Mock the response generation API
        await page.route('**/api/v1/response/generate', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    content: 'Tell me more about this investment opportunity!',
                    generation_time_ms: 2500,
                    safety_validated: true,
                    regeneration_count: 0,
                    used_fallback_model: false,
                    message_id: 'msg-restore-123',
                    turn_count: 1,
                    turn_limit: 20
                })
            });
        });

        // Start a session
        await page.getByTestId('email-input-textarea').fill('Invest now for guaranteed 500% returns!');
        await page.getByTestId('analyze-button').click();
        await waitForAnalysisResult(page);

        // Generate first response
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Verify session ID is in URL
        await expect(page).toHaveURL(new RegExp(`session=${sessionId}`));

        // Mock the restore API for after refresh
        await page.route('**/api/v1/session/*/restore', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: sessionId,
                    status: 'active',
                    attack_type: 'crypto_investment',
                    attack_type_display: 'Crypto Investment Scam',
                    confidence: 88,
                    persona: {
                        persona_type: 'greedy_investor',
                        name: 'Robert Chen',
                        age: 45,
                        style_description: 'Eager and quick to act',
                        background: 'Day trader'
                    },
                    messages: [
                        {
                            id: 'msg-restore-123',
                            sender: 'bot',
                            content: 'Tell me more about this investment opportunity!',
                            timestamp: new Date().toISOString(),
                            thinking: null
                        }
                    ],
                    iocs: [],
                    turn_count: 1,
                    turn_limit: 20,
                    is_at_limit: false
                })
            });
        });

        // Re-open the dashboard from the session URL to exercise restoration.
        await page.goto(`/dashboard?session=${sessionId}`);

        // Verify session state is restored
        await expect(page.getByTestId('chat-message-bot')).toBeVisible({ timeout: 10000 });
        await expect(page.getByText('Tell me more about this investment opportunity!')).toBeVisible();
        await expect(page.getByText('Turn 1/20')).toBeVisible();
    });

    test('should restore IOCs and turn counter after refresh', async ({ page }) => {
        const sessionId = 'test-session-ioc-refresh-789';

        // Start with mocking all needed APIs
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95,
                    reasoning: '419 scam with payment request',
                    classification_time_ms: 500,
                    session_id: sessionId,
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'Margaret Thompson',
                        age: 72,
                        style_description: 'Trusting',
                        background: 'Retired'
                    }
                })
            });
        });

        await page.route('**/api/v1/response/generate', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    content: 'I am interested in your offer!',
                    generation_time_ms: 2000,
                    safety_validated: true,
                    regeneration_count: 0,
                    used_fallback_model: false,
                    message_id: 'msg-ioc-123',
                    turn_count: 1,
                    turn_limit: 20
                })
            });
        });

        // Create session
        await page.getByTestId('email-input-textarea').fill('Dear Friend, send money to claim prize');
        await page.getByTestId('analyze-button').click();
        await waitForAnalysisResult(page);
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Mock restore API with IOCs
        await page.route('**/api/v1/session/*/restore', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: sessionId,
                    status: 'active',
                    attack_type: 'nigerian_419',
                    attack_type_display: 'Nigerian 419 Scam',
                    confidence: 95,
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'Margaret Thompson',
                        age: 72,
                        style_description: 'Trusting',
                        background: 'Retired'
                    },
                    messages: [
                        {
                            id: 'msg-ioc-123',
                            sender: 'bot',
                            content: 'I am interested in your offer!',
                            timestamp: new Date().toISOString(),
                            thinking: null
                        },
                        {
                            id: 'msg-scam-456',
                            sender: 'scammer',
                            content: 'Send money to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                            timestamp: new Date().toISOString(),
                            thinking: null
                        },
                        {
                            id: 'msg-bot-789',
                            sender: 'bot',
                            content: 'How do I send money?',
                            timestamp: new Date().toISOString(),
                            thinking: null
                        }
                    ],
                    iocs: [
                        {
                            id: 'ioc-btc-123',
                            type: 'btc',
                            value: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                            is_high_value: true,
                            created_at: new Date().toISOString()
                        }
                    ],
                    turn_count: 2,
                    turn_limit: 20,
                    is_at_limit: false
                })
            });
        });

        // Re-open the dashboard from the session URL to exercise restoration.
        await page.goto(`/dashboard?session=${sessionId}`);

        // Verify messages are restored
        const botMessages = page.getByTestId('chat-message-bot');
        await expect(botMessages).toHaveCount(2, { timeout: 10000 });

        const scammerMessages = page.getByTestId('chat-message-scammer');
        await expect(scammerMessages).toHaveCount(1);

        // Verify turn counter is correct
        await expect(page.getByTestId('turn-counter')).toHaveText('Turn 2/20');

        // Verify IOC is displayed in Intel Dashboard
        await page.getByRole('button', { name: 'Expand intel panel' }).click();
        await expect(page.getByText('bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh').first()).toBeVisible();
    });

    test('should clear session from URL on new session', async ({ page }) => {
        const sessionId = 'test-session-clear-url';

        // Mock APIs
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'fake_invoice',
                    confidence: 85,
                    reasoning: 'Fake invoice detected',
                    classification_time_ms: 400,
                    session_id: sessionId,
                    persona: {
                        persona_type: 'stressed_manager',
                        name: 'Jennifer Walsh',
                        age: 38,
                        style_description: 'Professional',
                        background: 'Office manager'
                    }
                })
            });
        });

        // Start session
        await page.getByTestId('email-input-textarea').fill('Please pay this invoice immediately');
        await page.getByTestId('analyze-button').click();
        await waitForAnalysisResult(page);

        // Verify session ID is in URL
        await expect(page).toHaveURL(new RegExp(`session=${sessionId}`));

        // Click new session button
        await page.getByTestId('new-session-header-button').click();

        // Confirm in dialog - use the data-testid for the confirm button
        await expect(page.getByTestId('new-session-dialog')).toBeVisible();
        await page.getByTestId('new-session-confirm-button').click();

        // Verify URL no longer contains session ID
        await expect(page).not.toHaveURL(new RegExp('session='));
        await expect(page).toHaveURL('/dashboard');
    });

    test('should handle non-existent session gracefully', async ({ page }) => {
        // Mock restore API to return 404
        await page.route('**/api/v1/session/*/restore', async route => {
            await route.fulfill({
                status: 404,
                contentType: 'application/json',
                body: JSON.stringify({
                    detail: 'Session not found'
                })
            });
        });

        // Navigate directly to dashboard with a fake session ID
        await page.goto('/dashboard?session=non-existent-session-id');

        // Page should clear the invalid session and show fresh dashboard
        await expect(page.getByTestId('email-input-textarea')).toBeVisible();
        // URL should be cleared
        await expect(page).toHaveURL('/dashboard');
    });

    test('should allow continuing conversation after restore', async ({ page }) => {
        const sessionId = 'test-session-continue-after-restore';

        // Set up initial session
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'romance_scam',
                    confidence: 90,
                    reasoning: 'Romance scam detected',
                    classification_time_ms: 450,
                    session_id: sessionId,
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'Dorothy Miller',
                        age: 65,
                        style_description: 'Lonely and trusting',
                        background: 'Widowed teacher'
                    }
                })
            });
        });

        await page.route('**/api/v1/response/generate', async route => {
            const request = route.request();
            const body = request.postDataJSON();

            if (!body.scammer_message) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'You sound so kind!',
                        generation_time_ms: 2000,
                        safety_validated: true,
                        regeneration_count: 0,
                        used_fallback_model: false,
                        message_id: 'msg-romance-1',
                        turn_count: 1,
                        turn_limit: 20
                    })
                });
            } else {
                // Response after scammer input (after restore)
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'I would love to help you!',
                        generation_time_ms: 2200,
                        safety_validated: true,
                        regeneration_count: 0,
                        used_fallback_model: false,
                        message_id: 'msg-romance-2',
                        scammer_message_id: 'scam-romance-1',
                        turn_count: 2,
                        turn_limit: 20,
                        extracted_iocs: []
                    })
                });
            }
        });

        // Start session and generate response
        await page.getByTestId('email-input-textarea').fill('My dear, I am a soldier stationed overseas...');
        await page.getByTestId('analyze-button').click();
        await waitForAnalysisResult(page);
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Mock restore API
        await page.route('**/api/v1/session/*/restore', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: sessionId,
                    status: 'active',
                    attack_type: 'romance_scam',
                    attack_type_display: 'Romance Scam',
                    confidence: 90,
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'Dorothy Miller',
                        age: 65,
                        style_description: 'Lonely and trusting',
                        background: 'Widowed teacher'
                    },
                    messages: [
                        {
                            id: 'msg-romance-1',
                            sender: 'bot',
                            content: 'You sound so kind!',
                            timestamp: new Date().toISOString(),
                            thinking: null
                        }
                    ],
                    iocs: [],
                    turn_count: 1,
                    turn_limit: 20,
                    is_at_limit: false
                })
            });
        });

        // Re-open the dashboard from the session URL to exercise restoration.
        await page.goto(`/dashboard?session=${sessionId}`);

        // Verify we can continue the conversation by submitting a scammer message
        await expect(page.getByText('You sound so kind!')).toBeVisible({ timeout: 10000 });
        await expect(page.getByTestId('scammer-input-textarea')).toBeVisible();
        await page.getByTestId('scammer-input-textarea').fill('I need $500 for an emergency');
        await page.getByTestId('scammer-input-send-button').click();

        // Should see the new response
        await expect(page.getByText('I would love to help you!')).toBeVisible();
        await expect(page.getByText('Turn 2/20')).toBeVisible();
    });
});
