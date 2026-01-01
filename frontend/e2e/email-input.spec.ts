import { test, expect } from '@playwright/test';

test.describe('Email Input & Analysis Flow', () => {
    test.beforeEach(async ({ page }) => {
        // Go directly to register page
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `test-${timestamp}-${random}@example.com`;
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

    test('should allow pasting email and analyzing', async ({ page }) => {
        // Check for presence of key elements
        const heading = page.getByRole('heading', { name: 'Paste Phishing Email' });
        await expect(heading).toBeVisible();

        const textarea = page.getByPlaceholder('Paste phishing email content here...');
        await expect(textarea).toBeVisible();

        const analyzeButton = page.locator('#analyze-button');
        await expect(analyzeButton).toBeVisible();
        await expect(analyzeButton).toBeDisabled(); // Initially disabled

        // Valid input test
        const validEmail = 'Subject: Urgent\nFrom: boss@ceo.com\nPlease send money now.';
        await textarea.fill(validEmail);

        // Check character counter
        await expect(page.getByText(`${validEmail.length.toLocaleString()} / 50,000`)).toBeVisible();

        // Button should be enabled
        await expect(analyzeButton).toBeEnabled();

        // Mock the backend API response
        await page.route('*/**/api/v1/analysis', async route => {
            console.log('API Mock hit for /analysis');
            // Simulate processing delay
            await new Promise(resolve => setTimeout(resolve, 1500));
            await route.fulfill({
                status: 202,
                contentType: 'application/json',
                body: JSON.stringify({
                    analysis_id: '123e4567-e89b-12d3-a456-426614174000',
                    content_preview: 'Subject: Urgent...',
                    status: 'processing'
                })
            });
        });

        // Click analyze
        await analyzeButton.click();

        // Should show loading state
        await expect(page.getByText('Analyzing...')).toBeVisible();
        await expect(analyzeButton).toBeDisabled();

        // Wait for "analysis" to complete
        await expect(page.getByText('Analyzing...')).not.toBeVisible({ timeout: 5000 });
        await expect(analyzeButton).toBeEnabled();
        await expect(analyzeButton).toHaveText('Analyze');
    });

    test('should validate input length', async ({ page }) => {
        const textarea = page.getByPlaceholder('Paste phishing email content here...');
        const analyzeButton = page.getByRole('button', { name: 'Analyze' });

        // Too short input
        await textarea.fill('short');
        await expect(page.getByText('Email must be at least 10 characters')).toBeVisible();
        await expect(analyzeButton).toBeDisabled();

        // Correct input
        await textarea.fill('Long enough email content for validation.');
        await expect(page.getByText('Email must be at least 10 characters')).not.toBeVisible();
        await expect(analyzeButton).toBeEnabled();
    });
});
