import { test, expect } from '@playwright/test';

test.describe('Edit Generated Response (US-008)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-edit-${timestamp}-${random}@example.com`;
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
                    session_id: 'test-session-edit-123',
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
                    message_id: 'msg-edit-test-123'
                })
            });
        });

        // Input email and analyze
        await page.getByTestId('email-input-textarea').fill('Dear Friend, I am a Nigerian Prince...');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByText('Nigerian 419').first()).toBeVisible();

        // Generate response
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();
    });

    test('should show edit button for bot messages', async ({ page }) => {
        await expect(page.getByTestId('edit-response-button')).toBeVisible();
        await expect(page.getByText('Edit', { exact: true })).toBeVisible();
    });

    test('should enter edit mode when edit button is clicked', async ({ page }) => {
        await page.getByTestId('edit-response-button').click();

        // Textarea should be visible
        await expect(page.getByTestId('edit-response-textarea')).toBeVisible();

        // Save and Cancel buttons should be visible
        await expect(page.getByTestId('save-edit-button')).toBeVisible();
        await expect(page.getByTestId('cancel-edit-button')).toBeVisible();

        // Edit button should not be visible
        await expect(page.getByTestId('edit-response-button')).not.toBeVisible();
    });

    test('should restore original content when cancel is clicked', async ({ page }) => {
        const originalContent = 'Oh my goodness! This sounds like a wonderful opportunity.';

        await page.getByTestId('edit-response-button').click();

        // Modify the content
        const textarea = page.getByTestId('edit-response-textarea');
        await textarea.fill('Modified content that should be discarded');

        // Click cancel
        await page.getByTestId('cancel-edit-button').click();

        // Should exit edit mode
        await expect(page.getByTestId('edit-response-textarea')).not.toBeVisible();
        await expect(page.getByTestId('edit-response-button')).toBeVisible();

        // Original content should be displayed
        await expect(page.getByText(originalContent)).toBeVisible();
    });

    test('should save valid edited content', async ({ page }) => {
        const newContent = 'This is my edited response.';

        // Mock the validation API to return safe
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

        // Edit the content
        const textarea = page.getByTestId('edit-response-textarea');
        await textarea.fill(newContent);

        // Save
        await page.getByTestId('save-edit-button').click();

        // Should exit edit mode and show new content
        await expect(page.getByTestId('edit-response-textarea')).not.toBeVisible();
        await expect(page.getByText(newContent)).toBeVisible();
    });

    test('should show validation error for unsafe content', async ({ page }) => {
        const unsafeContent = 'My SSN is 234-56-7890';

        // Mock the validation API to return unsafe
        await page.route('**/api/v1/response/validate', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    is_safe: false,
                    violations: ['ssn: Social Security Number detected']
                })
            });
        });

        await page.getByTestId('edit-response-button').click();

        // Edit with unsafe content
        const textarea = page.getByTestId('edit-response-textarea');
        await textarea.fill(unsafeContent);

        // Try to save
        await page.getByTestId('save-edit-button').click();

        // Should show validation error and stay in edit mode
        await expect(page.getByText(/Unsafe content detected/i)).toBeVisible();
        await expect(page.getByTestId('edit-response-textarea')).toBeVisible();
    });

    test('should show loading state during validation', async ({ page }) => {
        // Mock the validation API with delay
        await page.route('**/api/v1/response/validate', async route => {
            await new Promise(resolve => setTimeout(resolve, 1000));
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
        await page.getByTestId('edit-response-textarea').fill('New safe content');
        await page.getByTestId('save-edit-button').click();

        // Should show validating state
        await expect(page.getByText('Validating...')).toBeVisible();
    });

    test('should not allow saving empty content', async ({ page }) => {
        await page.getByTestId('edit-response-button').click();

        // Clear the content
        const textarea = page.getByTestId('edit-response-textarea');
        await textarea.fill('');

        // Save button should be disabled
        await expect(page.getByTestId('save-edit-button')).toBeDisabled();
    });
});

test.describe('Copy Response to Clipboard (US-009)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-copy-${timestamp}-${random}@example.com`;
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

    test('should show copy button for bot messages', async ({ page }) => {
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
                    session_id: 'test-session-copy-123',
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
                    message_id: 'msg-copy-test-123'
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

    test('should show copied confirmation when clicking copy button', async ({ page, context }) => {
        // Grant clipboard permissions (clipboard-write not supported in WebKit/mobile-safari)
        try {
            await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        } catch {
            await context.grantPermissions(['clipboard-read']);
        }

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
                    session_id: 'test-session-copy-confirm-123',
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
                    content: 'Hello! This is test content to copy.',
                    generation_time_ms: 2500,
                    safety_validated: true,
                    regeneration_count: 0,
                    used_fallback_model: false,
                    message_id: 'msg-copy-confirm-123'
                })
            });
        });

        // Input, analyze, generate
        await page.getByTestId('email-input-textarea').fill('Dear Friend...');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByText('Nigerian 419').first()).toBeVisible();

        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Click copy button
        await page.getByTestId('copy-response-button').click();

        // Should show "Copied!" confirmation
        await expect(page.getByText('Copied!')).toBeVisible();

        // Wait and verify it disappears after 2 seconds
        await page.waitForTimeout(2500);
        await expect(page.getByText('Copied!')).not.toBeVisible();
        await expect(page.getByText('Copy to clipboard')).toBeVisible();
    });
});
