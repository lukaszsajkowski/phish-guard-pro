import { test, expect } from '@playwright/test';

test.describe('Attack Type Classification', () => {
    test.beforeEach(async ({ page }) => {
        // Go directly to register page
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `test-class-${timestamp}-${random}@example.com`;
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

    test('should classify phishing email correctly', async ({ page }) => {
        // Mock the analysis API
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95.5,
                    reasoning: 'Classic 419 indicators detected',
                    classification_time_ms: 500
                })
            });
        });

        // Input email content
        const emailContent = 'Dear Friend, I am a Prince...';
        await page.getByTestId('email-input-textarea').fill(emailContent);

        // Click analyze
        await page.getByTestId('analyze-button').click();

        // Verification
        await expect(page.getByText('Nigerian 419')).toBeVisible();
        await expect(page.getByText('95.5% Confidence')).toBeVisible();
        await expect(page.getByText('Classic 419 indicators detected')).toBeVisible();
    });
});
