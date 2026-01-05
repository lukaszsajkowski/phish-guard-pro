import { test, expect } from '@playwright/test';

test.describe('Paste Scammer Response (US-010)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-scammer-${timestamp}-${random}@example.com`;
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

    test('should show scammer input after generating first response', async ({ page }) => {
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
                    session_id: 'test-session-123',
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

        // Mock the response generation API
        await page.route('**/api/v1/response/generate', async route => {
            const request = route.request();
            const body = request.postDataJSON();

            // First call - no scammer message
            if (!body.scammer_message) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'Oh my goodness! This sounds wonderful!',
                        generation_time_ms: 2500,
                        safety_validated: true,
                        regeneration_count: 0,
                        used_fallback_model: false,
                        message_id: 'msg-123'
                    })
                });
            }
        });

        // Input email content
        const emailContent = 'Dear Friend, I am a Nigerian Prince with $5 million to share...';
        await page.getByTestId('email-input-textarea').fill(emailContent);

        // Click analyze
        await page.getByTestId('analyze-button').click();
        await expect(page.getByText('Nigerian 419')).toBeVisible();

        // Generate first response
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Should show scammer input
        await expect(page.getByTestId('scammer-input-textarea')).toBeVisible();
        await expect(page.getByTestId('scammer-input-send-button')).toBeVisible();
    });

    test('should submit scammer message and receive new response', async ({ page }) => {
        let requestCount = 0;

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
                    session_id: 'test-session-123',
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

        // Mock the response generation API
        await page.route('**/api/v1/response/generate', async route => {
            requestCount++;
            const request = route.request();
            const body = request.postDataJSON();

            if (!body.scammer_message) {
                // First call - initial response
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'Oh my goodness! This sounds wonderful!',
                        generation_time_ms: 2500,
                        safety_validated: true,
                        regeneration_count: 0,
                        used_fallback_model: false,
                        message_id: 'msg-123'
                    })
                });
            } else {
                // Second call - with scammer message
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'Oh dear! How would I send the money?',
                        generation_time_ms: 2500,
                        safety_validated: true,
                        regeneration_count: 0,
                        used_fallback_model: false,
                        message_id: 'msg-456',
                        scammer_message_id: 'scam-msg-123',
                        extracted_iocs: []
                    })
                });
            }
        });

        // Input email content
        await page.getByTestId('email-input-textarea').fill('Dear Friend...');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByText('Nigerian 419')).toBeVisible();

        // Generate first response
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Enter scammer response
        const scammerMessage = 'Please send $100 to get started with the transfer.';
        await page.getByTestId('scammer-input-textarea').fill(scammerMessage);

        // Submit
        await page.getByTestId('scammer-input-send-button').click();

        // Should show scammer message in chat
        await expect(page.getByTestId('chat-message-scammer')).toBeVisible();
        await expect(page.getByText(scammerMessage)).toBeVisible();

        // Should show second bot response
        await expect(page.getByText('Oh dear! How would I send the money?')).toBeVisible();

        // Verify two bot messages exist
        const botMessages = page.getByTestId('chat-message-bot');
        await expect(botMessages).toHaveCount(2);
    });

    test('should display scammer message with correct styling', async ({ page }) => {
        // Mock APIs
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'crypto_investment',
                    confidence: 88,
                    reasoning: 'Crypto scam detected',
                    classification_time_ms: 400,
                    session_id: 'test-session-456',
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

        await page.route('**/api/v1/response/generate', async route => {
            const request = route.request();
            const body = request.postDataJSON();

            if (!body.scammer_message) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'Interesting! Tell me more about this investment.',
                        generation_time_ms: 2000,
                        safety_validated: true,
                        regeneration_count: 0,
                        used_fallback_model: false,
                        message_id: 'msg-789'
                    })
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'How do I start?',
                        generation_time_ms: 1500,
                        safety_validated: true,
                        regeneration_count: 0,
                        used_fallback_model: false,
                        message_id: 'msg-101',
                        scammer_message_id: 'scam-msg-456',
                        extracted_iocs: []
                    })
                });
            }
        });

        // Setup
        await page.getByTestId('email-input-textarea').fill('Invest in crypto for guaranteed 500% returns!');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByText('Crypto Investment')).toBeVisible();

        // Generate first response
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Submit scammer message
        await page.getByTestId('scammer-input-textarea').fill('Send BTC to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh');
        await page.getByTestId('scammer-input-send-button').click();

        // Verify scammer message appears with "Scammer" label
        const scammerMessage = page.getByTestId('chat-message-scammer');
        await expect(scammerMessage).toBeVisible();
        await expect(scammerMessage.getByText('Scammer')).toBeVisible();
    });

    test('should update turn counter after scammer message', async ({ page }) => {
        // Mock APIs
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'ceo_fraud',
                    confidence: 92,
                    reasoning: 'CEO impersonation detected',
                    classification_time_ms: 350,
                    session_id: 'test-session-789',
                    persona: {
                        persona_type: 'stressed_manager',
                        name: 'Jennifer Walsh',
                        age: 38,
                        style_description: 'Professional but rushed',
                        background: 'Office manager'
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
                        content: 'Sure, I can process that payment.',
                        generation_time_ms: 2000,
                        safety_validated: true,
                        regeneration_count: 0,
                        used_fallback_model: false,
                        message_id: 'msg-turn1'
                    })
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'What are the wire details?',
                        generation_time_ms: 1800,
                        safety_validated: true,
                        regeneration_count: 0,
                        used_fallback_model: false,
                        message_id: 'msg-turn2',
                        scammer_message_id: 'scam-turn1',
                        extracted_iocs: []
                    })
                });
            }
        });

        // Setup and generate first response
        await page.getByTestId('email-input-textarea').fill('Wire $50,000 urgently - CEO request');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByText('CEO Fraud')).toBeVisible();

        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Check turn counter shows Turn 1/20
        await expect(page.getByText('Turn 1/20')).toBeVisible();

        // Submit scammer message
        await page.getByTestId('scammer-input-textarea').fill('Use this IBAN: DE89370400440532013000');
        await page.getByTestId('scammer-input-send-button').click();

        // Wait for second response
        await expect(page.getByText('What are the wire details?')).toBeVisible();

        // Turn counter should now show Turn 2/20
        await expect(page.getByText('Turn 2/20')).toBeVisible();
    });

    test('should validate minimum character length', async ({ page }) => {
        // Mock APIs
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'lottery_prize',
                    confidence: 90,
                    reasoning: 'Prize scam detected',
                    classification_time_ms: 300,
                    session_id: 'test-session-val',
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'Betty Wilson',
                        age: 68,
                        style_description: 'Hopeful and trusting',
                        background: 'Retired nurse'
                    }
                })
            });
        });

        await page.route('**/api/v1/response/generate', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    content: 'I won? How exciting!',
                    generation_time_ms: 1500,
                    safety_validated: true,
                    regeneration_count: 0,
                    used_fallback_model: false,
                    message_id: 'msg-val'
                })
            });
        });

        // Setup
        await page.getByTestId('email-input-textarea').fill('You won $1 million!');
        await page.getByTestId('analyze-button').click();
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Send button should be disabled when empty
        const sendButton = page.getByTestId('scammer-input-send-button');
        await expect(sendButton).toBeDisabled();

        // Type something to enable
        await page.getByTestId('scammer-input-textarea').fill('Hello');
        await expect(sendButton).toBeEnabled();

        // Clear and verify disabled again
        await page.getByTestId('scammer-input-textarea').fill('');
        await expect(sendButton).toBeDisabled();
    });
});
