import { test, expect } from '@playwright/test';
import { waitForIntelDashboard } from './helpers/dashboard';

test.describe('Safe Email Handling', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login flow
        await page.goto('/register');
        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-safe-${timestamp}-${random}@example.com`;
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

    test('should warn user when email is classified as safe', async ({ page }) => {
        // Mock API response for safe email
        await page.route('**/api/v1/classification/analyze', async route => {
            const request = route.request();
            const postData = request.postDataJSON();

            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'not_phishing',
                    confidence: 15.0, // Low confidence safe email
                    reasoning: 'No threats detected',
                    classification_time_ms: 300
                })
            });
        });

        // 1. Paste email and analyze
        await page.getByTestId('email-input-textarea').fill('Just a friendly hello.');
        await page.getByTestId('analyze-button').click();

        // 2. Expect Warning Dialog
        await expect(page.getByRole('alertdialog')).toBeVisible();
        await expect(page.getByText('Possible Safe Email Detected')).toBeVisible();

        // 3. Test "Paste different email" (Reset)
        await page.getByRole('button', { name: 'Paste different email' }).click();
        await expect(page.getByRole('alertdialog')).toBeHidden();
        await expect(page.getByTestId('email-input-textarea')).toBeEmpty();

        // 4. Retry and test "Continue anyway"
        await page.getByTestId('email-input-textarea').fill('Just a friendly hello again.');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByRole('alertdialog')).toBeVisible();
        await page.getByRole('button', { name: 'Continue anyway' }).click();

        // 5. Expect Result Card (Green)
        await expect(page.getByRole('alertdialog')).toBeHidden();
        await waitForIntelDashboard(page);
        await expect(page.getByText('Not Phishing').first()).toBeVisible();
        await expect(page.getByText('Legitimate Email Detected')).toBeVisible();
    });
});
