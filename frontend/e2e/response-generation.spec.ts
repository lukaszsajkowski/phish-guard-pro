import { test, expect } from '@playwright/test';

test.describe('Generate First Response (US-007)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-response-${timestamp}-${random}@example.com`;
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

    test('should show generate response button after classification', async ({ page }) => {
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

        // Input email content
        const emailContent = 'Dear Friend, I am a Nigerian Prince with $5 million to share...';
        await page.getByTestId('email-input-textarea').fill(emailContent);

        // Click analyze
        await page.getByTestId('analyze-button').click();

        // Wait for classification to complete
        await expect(page.getByText('Nigerian 419').first()).toBeVisible();

        // Should show the generate response button
        await expect(page.getByTestId('generate-response-button')).toBeVisible();
        await expect(page.getByText('Generate Response')).toBeVisible();
    });

    test('should generate response when button is clicked', async ({ page }) => {
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
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    content: 'Oh my goodness! This sounds like a wonderful opportunity. But I must ask - how did you find my email address? My grandson always tells me to be careful online.',
                    generation_time_ms: 2500,
                    safety_validated: true,
                    regeneration_count: 0,
                    used_fallback_model: false,
                    thinking: {
                        turn_goal: 'Build rapport and gather information',
                        selected_tactic: 'Ask Questions',
                        reasoning: 'Starting with interest while asking for details about how they found me.'
                    },
                    message_id: 'msg-123'
                })
            });
        });

        // Input email content
        const emailContent = 'Dear Friend, I am a Nigerian Prince with $5 million to share...';
        await page.getByTestId('email-input-textarea').fill(emailContent);

        // Click analyze
        await page.getByTestId('analyze-button').click();

        // Wait for classification to complete
        await expect(page.getByText('Nigerian 419').first()).toBeVisible();

        // Click generate response
        await page.getByTestId('generate-response-button').click();

        // Should show the generated response
        await expect(page.getByText('Oh my goodness!')).toBeVisible({ timeout: 10000 });
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();
    });

    test('should display copy button for generated response', async ({ page }) => {
        // Mock APIs
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

        await page.route('**/api/v1/response/generate', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    content: 'Hello there! This sounds interesting.',
                    generation_time_ms: 2500,
                    safety_validated: true,
                    regeneration_count: 0,
                    used_fallback_model: false,
                    message_id: 'msg-123'
                })
            });
        });

        // Input and analyze
        await page.getByTestId('email-input-textarea').fill('Dear Friend...');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByText('Nigerian 419').first()).toBeVisible();

        // Generate response
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Verify copy button is present
        await expect(page.getByTestId('copy-response-button')).toBeVisible();
        await expect(page.getByText('Copy to clipboard')).toBeVisible();
    });

    test('should show loading state during generation', async ({ page }) => {
        // Mock classification
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95.5,
                    reasoning: 'Classic 419 indicators',
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

        // Mock response with delay
        await page.route('**/api/v1/response/generate', async route => {
            await new Promise(resolve => setTimeout(resolve, 1000));
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    content: 'Hello!',
                    generation_time_ms: 1000,
                    safety_validated: true,
                    regeneration_count: 0,
                    used_fallback_model: false,
                    message_id: 'msg-123'
                })
            });
        });

        // Setup
        await page.getByTestId('email-input-textarea').fill('Dear Friend...');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByText('Nigerian 419').first()).toBeVisible();

        // Click generate and check loading state
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByText('Generating...')).toBeVisible();
    });

    test('should not show chat area for not_phishing classification', async ({ page }) => {
        // Mock classification as not phishing
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'not_phishing',
                    confidence: 85,
                    reasoning: 'This appears to be a legitimate email',
                    classification_time_ms: 500,
                    session_id: 'test-session-123'
                })
            });
        });

        await page.getByTestId('email-input-textarea').fill('Hello, just following up on our meeting.');
        await page.getByTestId('analyze-button').click();

        // Should show safe email warning dialog
        await expect(page.getByText('Possible Safe Email Detected')).toBeVisible();

        // Should NOT show generate response button
        await expect(page.getByTestId('generate-response-button')).not.toBeVisible();
    });
});
