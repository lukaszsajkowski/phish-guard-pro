import { test, expect } from '@playwright/test';

/**
 * E2E tests for US-001: User Registration
 * 
 * Tests the registration page functionality including:
 * - Page elements and initial state
 * - Client-side validation
 * - Success redirect flow
 */

test.describe('Registration Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/register');
    });

    test.describe('Page Elements', () => {
        test('should display all required form elements', async ({ page }) => {
            // Verify heading
            await expect(page.getByRole('heading', { name: 'Create an account' })).toBeVisible();

            // Verify form fields
            await expect(page.locator('#email')).toBeVisible();
            await expect(page.locator('#password')).toBeVisible();
            await expect(page.locator('#confirm-password')).toBeVisible();

            // Verify submit button
            await expect(page.locator('#register-button')).toBeVisible();
        });

        test('should have register button disabled initially', async ({ page }) => {
            await expect(page.locator('#register-button')).toBeDisabled();
        });

        test('should have link to login page', async ({ page }) => {
            const loginLink = page.getByRole('link', { name: 'Sign in' });
            await expect(loginLink).toBeVisible();
            await expect(loginLink).toHaveAttribute('href', '/login');
        });
    });

    test.describe('Email Validation', () => {
        test('should show error for invalid email format', async ({ page }) => {
            await page.locator('#email').fill('invalid-email');
            await page.locator('#password').click(); // Blur email field

            await expect(page.getByText('Please enter a valid email address')).toBeVisible();
        });

        test('should not show error for valid email', async ({ page }) => {
            await page.locator('#email').fill('test@example.com');
            await page.locator('#password').click();

            await expect(page.getByText('Please enter a valid email address')).not.toBeVisible();
        });
    });

    test.describe('Password Validation', () => {
        test('should show error for password shorter than 8 characters', async ({ page }) => {
            await page.locator('#password').fill('short');
            await page.locator('#confirm-password').click(); // Blur password field

            await expect(page.getByText('Password must be at least 8 characters')).toBeVisible();
        });

        test('should not show error for password with 8+ characters', async ({ page }) => {
            await page.locator('#password').fill('validpass123');
            await page.locator('#confirm-password').click();

            await expect(page.getByText('Password must be at least 8 characters')).not.toBeVisible();
        });
    });

    test.describe('Password Confirmation', () => {
        test('should show error when passwords do not match', async ({ page }) => {
            await page.locator('#password').fill('validpass123');
            await page.locator('#confirm-password').fill('differentpass');
            await page.locator('#email').click(); // Blur confirm password field

            await expect(page.getByText('Passwords do not match')).toBeVisible();
        });

        test('should not show error when passwords match', async ({ page }) => {
            await page.locator('#password').fill('validpass123');
            await page.locator('#confirm-password').fill('validpass123');
            await page.locator('#email').click();

            await expect(page.getByText('Passwords do not match')).not.toBeVisible();
        });
    });

    test.describe('Form Submission', () => {
        test('should enable register button when all fields are valid', async ({ page }) => {
            await page.locator('#email').fill('test@example.com');
            await page.locator('#password').fill('validpass123');
            await page.locator('#confirm-password').fill('validpass123');

            await expect(page.locator('#register-button')).toBeEnabled();
        });

        test('should keep button disabled with invalid email', async ({ page }) => {
            await page.locator('#email').fill('invalid');
            await page.locator('#password').fill('validpass123');
            await page.locator('#confirm-password').fill('validpass123');

            await expect(page.locator('#register-button')).toBeDisabled();
        });

        test('should keep button disabled with short password', async ({ page }) => {
            await page.locator('#email').fill('test@example.com');
            await page.locator('#password').fill('short');
            await page.locator('#confirm-password').fill('short');

            await expect(page.locator('#register-button')).toBeDisabled();
        });

        test('should keep button disabled with mismatched passwords', async ({ page }) => {
            await page.locator('#email').fill('test@example.com');
            await page.locator('#password').fill('validpass123');
            await page.locator('#confirm-password').fill('differentpass');

            await expect(page.locator('#register-button')).toBeDisabled();
        });
    });
});

test.describe('Login Page - Registration Success', () => {
    test('should display success message when redirected after registration', async ({ page }) => {
        await page.goto('/login?registered=true');

        await expect(page.locator('#registration-success-message')).toBeVisible();
        await expect(page.getByText('Registration successful')).toBeVisible();
    });

    test('should not display success message without query param', async ({ page }) => {
        await page.goto('/login');

        await expect(page.locator('#registration-success-message')).not.toBeVisible();
    });

    test('should have link back to registration', async ({ page }) => {
        await page.goto('/login');

        const registerLink = page.getByRole('link', { name: 'Create one' });
        await expect(registerLink).toBeVisible();
        await expect(registerLink).toHaveAttribute('href', '/register');
    });
});
