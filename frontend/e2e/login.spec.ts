import { test, expect } from '@playwright/test';

/**
 * E2E tests for US-002: User Login
 * 
 * Tests the login page functionality including:
 * - Page elements and initial state
 * - Client-side validation
 * - Form submission states
 * - Error handling display
 */

test.describe('Login Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/login');
    });

    test.describe('Page Elements', () => {
        test('should display all required form elements', async ({ page }) => {
            // Verify heading
            await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();

            // Verify form fields
            await expect(page.locator('#email')).toBeVisible();
            await expect(page.locator('#password')).toBeVisible();

            // Verify submit button
            await expect(page.locator('#login-button')).toBeVisible();
        });

        test('should have login button disabled initially', async ({ page }) => {
            await expect(page.locator('#login-button')).toBeDisabled();
        });

        test('should have link to registration page', async ({ page }) => {
            const registerLink = page.getByRole('link', { name: 'Create one' });
            await expect(registerLink).toBeVisible();
            await expect(registerLink).toHaveAttribute('href', '/register');
        });

        test('should display product header', async ({ page }) => {
            await expect(page.getByText('PhishGuard Pro', { exact: true })).toBeVisible();
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

    test.describe('Form Submission', () => {
        test('should enable login button when all fields are filled with valid email', async ({ page }) => {
            await page.locator('#email').fill('test@example.com');
            await page.locator('#password').fill('somepassword');

            await expect(page.locator('#login-button')).toBeEnabled();
        });

        test('should keep button disabled with invalid email', async ({ page }) => {
            await page.locator('#email').fill('invalid');
            await page.locator('#password').fill('somepassword');

            await expect(page.locator('#login-button')).toBeDisabled();
        });

        test('should keep button disabled with empty password', async ({ page }) => {
            await page.locator('#email').fill('test@example.com');
            // Password remains empty

            await expect(page.locator('#login-button')).toBeDisabled();
        });

        test('should keep button disabled with empty email', async ({ page }) => {
            await page.locator('#password').fill('somepassword');
            // Email remains empty

            await expect(page.locator('#login-button')).toBeDisabled();
        });
    });

    test.describe('Password Visibility Toggle', () => {
        test('should toggle password visibility', async ({ page }) => {
            const passwordInput = page.locator('#password');

            // Initially password should be hidden
            await expect(passwordInput).toHaveAttribute('type', 'password');

            // Fill in password
            await passwordInput.fill('testpassword');

            // Click toggle button (the button inside password field)
            await page.locator('#password ~ button').click();

            // Password should now be visible
            await expect(passwordInput).toHaveAttribute('type', 'text');

            // Click again to hide
            await page.locator('#password ~ button').click();

            // Password should be hidden again
            await expect(passwordInput).toHaveAttribute('type', 'password');
        });
    });
});

test.describe('Login Page - Registration Success Message', () => {
    test('should display success message when redirected after registration', async ({ page }) => {
        await page.goto('/?registered=true');

        await expect(page.locator('#registration-success-message')).toBeVisible();
        await expect(page.getByText('Registration successful')).toBeVisible();
    });

    test('should not display success message without query param', async ({ page }) => {
        await page.goto('/login');

        await expect(page.locator('#registration-success-message')).not.toBeVisible();
    });
});

test.describe('Dashboard Protection', () => {
    test('should redirect unauthenticated user from dashboard to login', async ({ page }) => {
        // Try to access dashboard directly without authentication
        await page.goto('/dashboard');

        // Should be redirected to login page
        await expect(page).toHaveURL(/\/(login)?$/);
    });
});
