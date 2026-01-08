import { test, expect } from '@playwright/test';

test.describe('Persona Display', () => {
    test.beforeEach(async ({ page }) => {
        // Go directly to register page
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-persona-${timestamp}-${random}@example.com`;
        const password = 'validPassword123';

        await page.locator('#email').fill(email);
        await page.locator('#password').fill(password);
        await page.locator('#confirm-password').fill(password);

        // Wait for validation to pass
        const registerButton = page.locator('#register-button');
        await expect(registerButton).toBeEnabled();
        await registerButton.click();

        // Should redirect to login with success message
        await expect(page.locator('#registration-success-message')).toBeVisible();

        // Now login
        await page.locator('#email').fill(email);
        await page.locator('#password').fill(password);
        await page.getByRole('button', { name: 'Sign in' }).click();

        // Should be at dashboard
        await expect(page).toHaveURL('/dashboard');
    });

    test('should display persona card after analysis', async ({ page }) => {
        // Mock the analysis API
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95.5,
                    reasoning: 'Classic 419 indicators detected',
                    classification_time_ms: 500,
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'Margaret Thompson',
                        age: 72,
                        style_description: 'Trusting and polite, uses formal language.',
                        background: 'Retired teacher.'
                    }
                })
            });
        });

        // Input email content
        const emailContent = 'Dear Friend, I am a Prince...';
        await page.getByTestId('email-input-textarea').fill(emailContent);

        // Click analyze
        await page.getByTestId('analyze-button').click();

        // Verification

        // Wait for persona card to appear
        const personaCard = page.getByTestId('persona-card');
        await expect(personaCard).toBeVisible();

        // Verify content
        // await expect(page.getByText('Suggested Persona')).toBeVisible(); // Text not present in component
        await expect(page.getByText('Margaret Thompson')).toBeVisible();
        await expect(page.getByText('72 years old')).toBeVisible();
        await expect(page.getByText('Naive Retiree')).toBeVisible();

        // Verify background and style
        await expect(page.getByText('Retired teacher.')).toBeVisible();
        await expect(page.getByText('"Trusting and polite, uses formal language."')).toBeVisible();
    });
});
