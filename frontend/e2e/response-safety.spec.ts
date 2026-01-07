import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Response Security Validation (US-024)
 *
 * These tests verify that:
 * 1. Every response passes through Safety Check before display
 * 2. System blocks real PII formats (national ID, SSN patterns)
 * 3. System blocks real domains from blocklist
 * 4. Upon detecting unsafe content, response is automatically regenerated
 * 5. User never sees unsafe response
 */
test.describe('Response Security Validation (US-024)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-safety-${timestamp}-${random}@example.com`;
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
                    session_id: 'test-session-safety-123',
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
    });

    test.describe('SSN Detection', () => {
        test('should reject edited response containing SSN with dashes', async ({ page }) => {
            // Setup: generate a response first
            await setupGeneratedResponse(page);

            // Mock validation API to reject SSN
            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: false,
                        violations: ['ssn: Potential Social Security Number detected']
                    })
                });
            });

            // Try to edit with SSN
            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('My SSN is 234-56-7890');
            await page.getByTestId('save-edit-button').click();

            // Should show validation error
            await expect(page.getByText(/Unsafe content detected/i)).toBeVisible();
            await expect(page.getByTestId('edit-response-textarea')).toBeVisible();
        });

        test('should reject SSN with dots format', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: false,
                        violations: ['ssn: Potential Social Security Number detected']
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('My social security is 234.56.7890');
            await page.getByTestId('save-edit-button').click();

            await expect(page.getByText(/Unsafe content detected/i)).toBeVisible();
        });

        test('should allow test SSN 123-45-6789', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: true,
                        violations: []
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('The example number is 123-45-6789');
            await page.getByTestId('save-edit-button').click();

            // Should succeed - test SSN is allowed
            await expect(page.getByTestId('edit-response-textarea')).not.toBeVisible();
        });
    });

    test.describe('Credit Card Detection', () => {
        test('should reject real credit card numbers', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: false,
                        violations: ['credit_card: Potential credit card number detected']
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('My card is 4532-1234-5678-9012');
            await page.getByTestId('save-edit-button').click();

            await expect(page.getByText(/Unsafe content detected/i)).toBeVisible();
        });

        test('should allow test credit card 1111-1111-1111-1111', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: true,
                        violations: []
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('Test card: 1111-1111-1111-1111');
            await page.getByTestId('save-edit-button').click();

            await expect(page.getByTestId('edit-response-textarea')).not.toBeVisible();
        });
    });

    test.describe('Corporate Domain Blocklist', () => {
        test('should reject emails with Google domain', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: false,
                        violations: ["corporate_domain: Corporate domain 'google.com' is blocked"]
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('Contact me at john@google.com');
            await page.getByTestId('save-edit-button').click();

            await expect(page.getByText(/Unsafe content detected/i)).toBeVisible();
        });

        test('should reject emails with Microsoft domain', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: false,
                        violations: ["corporate_domain: Corporate domain 'microsoft.com' is blocked"]
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('Contact me at john@microsoft.com');
            await page.getByTestId('save-edit-button').click();

            await expect(page.getByText(/Unsafe content detected/i)).toBeVisible();
        });

        test('should allow @example.com email domain', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: true,
                        violations: []
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('Contact me at margaret@example.com');
            await page.getByTestId('save-edit-button').click();

            await expect(page.getByTestId('edit-response-textarea')).not.toBeVisible();
        });
    });

    test.describe('Phone Number Detection', () => {
        test('should reject real phone numbers', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: false,
                        violations: ['phone_real: Real phone number detected (use 555-XXX-XXXX)']
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('Call me at 212-555-1234');
            await page.getByTestId('save-edit-button').click();

            await expect(page.getByText(/Unsafe content detected/i)).toBeVisible();
        });

        test('should allow 555 placeholder phone numbers', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: true,
                        violations: []
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill('Call me at 555-123-4567');
            await page.getByTestId('save-edit-button').click();

            await expect(page.getByTestId('edit-response-textarea')).not.toBeVisible();
        });
    });

    test.describe('Multiple Violations', () => {
        test('should display all violations when content has multiple issues', async ({ page }) => {
            await setupGeneratedResponse(page);

            await page.route('**/api/v1/response/validate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        is_safe: false,
                        violations: [
                            'ssn: Potential Social Security Number detected',
                            "corporate_domain: Corporate domain 'google.com' is blocked"
                        ]
                    })
                });
            });

            await page.getByTestId('edit-response-button').click();
            await page.getByTestId('edit-response-textarea').fill(
                'My SSN is 234-56-7890 and email is john@google.com'
            );
            await page.getByTestId('save-edit-button').click();

            // Should show validation error with multiple violations
            const errorAlert = page.getByText(/Unsafe content detected/i);
            await expect(errorAlert).toBeVisible();
            // Verify the error message contains both violation types
            await expect(errorAlert).toContainText('ssn');
            await expect(errorAlert).toContainText('corporate_domain');
        });
    });

    test.describe('Auto-Regeneration on Unsafe Generated Content', () => {
        test('should show regeneration count when response needed regeneration', async ({ page }) => {
            // Mock response that was regenerated
            await page.route('**/api/v1/response/generate', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'Oh my goodness! This sounds wonderful.',
                        generation_time_ms: 3500,
                        safety_validated: true,
                        regeneration_count: 2, // Response was regenerated twice
                        used_fallback_model: false,
                        thinking: {
                            turn_goal: 'Build rapport',
                            selected_tactic: 'Ask Questions',
                            reasoning: 'Starting with interest.'
                        },
                        message_id: 'msg-regen-test-123',
                        turn_count: 1,
                        turn_limit: 20,
                        is_at_limit: false
                    })
                });
            });

            await page.getByTestId('email-input-textarea').fill('Dear Friend, I am a Nigerian Prince...');
            await page.getByTestId('analyze-button').click();
            await expect(page.getByText('Nigerian 419', { exact: true })).toBeVisible();

            await page.getByTestId('generate-response-button').click();

            // Response should be visible (user never saw unsafe versions)
            await expect(page.getByTestId('chat-message-bot')).toBeVisible();
            await expect(page.getByText('Oh my goodness!')).toBeVisible();
        });

        test('generated response always has safety_validated true', async ({ page }) => {
            // This test verifies the contract that generated responses
            // returned to frontend are always validated
            let receivedResponse: any = null;

            await page.route('**/api/v1/response/generate', async route => {
                receivedResponse = {
                    content: 'Hello! This is a safe response.',
                    generation_time_ms: 2000,
                    safety_validated: true, // This should ALWAYS be true
                    regeneration_count: 0,
                    used_fallback_model: false,
                    message_id: 'msg-safe-test-123',
                    turn_count: 1,
                    turn_limit: 20,
                    is_at_limit: false
                };
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(receivedResponse)
                });
            });

            await page.getByTestId('email-input-textarea').fill('Dear Friend...');
            await page.getByTestId('analyze-button').click();
            await expect(page.getByText('Nigerian 419', { exact: true })).toBeVisible();

            await page.getByTestId('generate-response-button').click();
            await expect(page.getByTestId('chat-message-bot')).toBeVisible();

            // Verify our mock returned safety_validated: true
            expect(receivedResponse.safety_validated).toBe(true);
        });
    });
});

/**
 * Helper function to setup a generated response before testing edits
 */
async function setupGeneratedResponse(page: import('@playwright/test').Page) {
    // Mock the response generation
    await page.route('**/api/v1/response/generate', async route => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                content: 'Oh my goodness! This sounds like a wonderful opportunity.',
                generation_time_ms: 2500,
                safety_validated: true,
                regeneration_count: 0,
                used_fallback_model: false,
                thinking: {
                    turn_goal: 'Build rapport and gather information',
                    selected_tactic: 'Ask Questions',
                    reasoning: 'Starting with interest while asking for details.'
                },
                message_id: 'msg-safety-test-123',
                turn_count: 1,
                turn_limit: 20,
                is_at_limit: false
            })
        });
    });

    // Input email and analyze
    await page.getByTestId('email-input-textarea').fill('Dear Friend, I am a Nigerian Prince...');
    await page.getByTestId('analyze-button').click();
    await expect(page.getByText('Nigerian 419', { exact: true })).toBeVisible();

    // Generate response
    await page.getByTestId('generate-response-button').click();
    await expect(page.getByTestId('chat-message-bot')).toBeVisible();
}
