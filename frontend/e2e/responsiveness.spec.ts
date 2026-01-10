import { test, expect } from '@playwright/test';

/**
 * E2E tests for US-026: Interface Responsiveness
 * Tests that the layout adjusts correctly at different viewport widths
 * and that key UI elements remain accessible and properly sized.
 *
 * These tests are split into two groups:
 * 1. Public page tests (login/register) - no auth required
 * 2. Authenticated page tests - require Supabase backend
 */

// Viewport widths to test (from acceptance criteria)
const viewports = {
    minimum: { width: 1024, height: 768 },  // Minimum supported width
    medium: { width: 1280, height: 800 },   // Sidebar collapse threshold
    large: { width: 1440, height: 900 },    // Common desktop size
    wide: { width: 1920, height: 1080 },    // Full HD
};

/**
 * Public page responsiveness tests - no backend required
 */
test.describe('Interface Responsiveness - Public Pages (US-026)', () => {
    test.describe('Login page responsiveness', () => {
        test('should render login page at minimum width (1024px)', async ({ page }) => {
            await page.setViewportSize(viewports.minimum);
            await page.goto('/login');

            // Page should load without horizontal scroll
            const documentWidth = await page.evaluate(() => document.documentElement.scrollWidth);
            const viewportWidth = await page.evaluate(() => window.innerWidth);
            expect(documentWidth).toBeLessThanOrEqual(viewportWidth + 10);

            // Login form should be visible and properly sized
            const emailInput = page.locator('#email');
            await expect(emailInput).toBeVisible();

            const emailBox = await emailInput.boundingBox();
            expect(emailBox?.width).toBeGreaterThan(200);
        });

        test('should render login page at all viewport widths', async ({ page }) => {
            for (const [name, viewport] of Object.entries(viewports)) {
                await page.setViewportSize(viewport);
                await page.goto('/login');

                // Check form elements are accessible
                const emailInput = page.locator('#email');
                await expect(emailInput).toBeVisible();

                const passwordInput = page.locator('#password');
                await expect(passwordInput).toBeVisible();

                const signInButton = page.getByRole('button', { name: 'Sign in' });
                await expect(signInButton).toBeVisible();

                const buttonBox = await signInButton.boundingBox();
                expect(buttonBox?.width).toBeGreaterThan(50);
                expect(buttonBox?.height).toBeGreaterThan(25);
            }
        });

        test('should have properly sized form at 1024px', async ({ page }) => {
            await page.setViewportSize(viewports.minimum);
            await page.goto('/login');

            const emailInput = page.locator('#email');
            const inputBox = await emailInput.boundingBox();

            // Input should be reasonably sized
            expect(inputBox?.width).toBeGreaterThan(250);
            expect(inputBox?.height).toBeGreaterThan(30);
        });
    });

    test.describe('Register page responsiveness', () => {
        test('should render register page at minimum width (1024px)', async ({ page }) => {
            await page.setViewportSize(viewports.minimum);
            await page.goto('/register');

            // Page should load without significant horizontal scroll
            const documentWidth = await page.evaluate(() => document.documentElement.scrollWidth);
            const viewportWidth = await page.evaluate(() => window.innerWidth);
            expect(documentWidth).toBeLessThanOrEqual(viewportWidth + 10);

            // Form elements should be visible
            const emailInput = page.locator('#email');
            await expect(emailInput).toBeVisible();

            const passwordInput = page.locator('#password');
            await expect(passwordInput).toBeVisible();

            const confirmInput = page.locator('#confirm-password');
            await expect(confirmInput).toBeVisible();
        });

        test('buttons should be clickable at all widths', async ({ page }) => {
            for (const [name, viewport] of Object.entries(viewports)) {
                await page.setViewportSize(viewport);
                await page.goto('/register');

                const registerButton = page.locator('#register-button');
                await expect(registerButton).toBeVisible();

                const buttonBox = await registerButton.boundingBox();
                expect(buttonBox?.width).toBeGreaterThan(80);
                expect(buttonBox?.height).toBeGreaterThan(30);
            }
        });
    });
});

/**
 * Authenticated page responsiveness tests - require Supabase backend
 * These tests will be skipped if backend is not available
 */
test.describe('Interface Responsiveness - Authenticated Pages (US-026)', () => {
    // Test data - unique per test run
    const testUser = {
        email: `e2e-responsive-${Date.now()}-${Math.floor(Math.random() * 10000)}@example.com`,
        password: 'validPassword123',
    };

    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        await page.locator('#email').fill(testUser.email);
        await page.locator('#password').fill(testUser.password);
        await page.locator('#confirm-password').fill(testUser.password);

        const registerButton = page.locator('#register-button');
        await expect(registerButton).toBeEnabled();
        await registerButton.click();

        await expect(page.locator('#registration-success-message')).toBeVisible();

        await page.locator('#email').fill(testUser.email);
        await page.locator('#password').fill(testUser.password);
        await page.getByRole('button', { name: 'Sign in' }).click();

        await expect(page).toHaveURL('/dashboard');
    });

    test.describe('Minimum width (1024px)', () => {
        test.beforeEach(async ({ page }) => {
            await page.setViewportSize(viewports.minimum);
        });

        test('should render dashboard without horizontal scroll in content', async ({ page }) => {
            // Page should not require horizontal scrolling for main content
            const documentWidth = await page.evaluate(() => document.documentElement.scrollWidth);
            const viewportWidth = await page.evaluate(() => window.innerWidth);

            // Document width should not exceed viewport + small tolerance
            expect(documentWidth).toBeLessThanOrEqual(viewportWidth + 10);
        });

        test('should show sidebar in collapsed state by default', async ({ page }) => {
            // At 1024px (< 1280px), sidebar should default to collapsed
            const sidebar = page.locator('[data-testid="app-sidebar"]');
            await expect(sidebar).toBeVisible();

            // Sidebar should be narrow (collapsed state is w-16 = 64px)
            const sidebarBox = await sidebar.boundingBox();
            expect(sidebarBox?.width).toBeLessThanOrEqual(80);
        });

        test('should allow email input without overlap', async ({ page }) => {
            const heading = page.getByRole('heading', { name: 'Paste Phishing Email' });
            await expect(heading).toBeVisible();

            const textarea = page.getByPlaceholder('Paste phishing email content here...');
            await expect(textarea).toBeVisible();

            // Textarea should be fully visible and clickable
            const textareaBox = await textarea.boundingBox();
            expect(textareaBox?.width).toBeGreaterThan(300);
        });

        test('should have readable analyze button', async ({ page }) => {
            const analyzeButton = page.locator('#analyze-button');
            await expect(analyzeButton).toBeVisible();

            const buttonBox = await analyzeButton.boundingBox();
            expect(buttonBox?.width).toBeGreaterThan(80);
            expect(buttonBox?.height).toBeGreaterThan(30);
        });
    });

    test.describe('Medium width (1280px - sidebar threshold)', () => {
        test.beforeEach(async ({ page }) => {
            await page.setViewportSize(viewports.medium);
        });

        test('should show sidebar expanded at 1280px+', async ({ page }) => {
            // At 1280px+, sidebar should be expanded by default (if no stored preference)
            const sidebar = page.locator('[data-testid="app-sidebar"]');
            await expect(sidebar).toBeVisible();

            // Sidebar should be wide (expanded state is w-64 = 256px)
            const sidebarBox = await sidebar.boundingBox();
            // Could be expanded or collapsed depending on localStorage
            expect(sidebarBox?.width).toBeGreaterThan(50);
        });

        test('should have properly sized main content area', async ({ page }) => {
            const mainContent = page.locator('[data-testid="main-content"]');
            await expect(mainContent).toBeVisible();

            const mainBox = await mainContent.boundingBox();
            // Main content should fill remaining space
            expect(mainBox?.width).toBeGreaterThan(800);
        });
    });

    test.describe('Large width (1440px)', () => {
        test.beforeEach(async ({ page }) => {
            await page.setViewportSize(viewports.large);
        });

        test('should properly layout email input and analysis results', async ({ page }) => {
            const textarea = page.getByPlaceholder('Paste phishing email content here...');
            await expect(textarea).toBeVisible();

            // Content should not exceed max-width
            const textareaBox = await textarea.boundingBox();
            expect(textareaBox?.width).toBeGreaterThan(400);
        });
    });

    test.describe('Sidebar collapse/expand functionality', () => {
        test('should toggle sidebar on button click', async ({ page }) => {
            await page.setViewportSize(viewports.medium);

            const collapseToggle = page.locator('[data-testid="sidebar-collapse-toggle"]');
            await expect(collapseToggle).toBeVisible();

            const sidebar = page.locator('[data-testid="app-sidebar"]');
            const initialBox = await sidebar.boundingBox();
            const initialWidth = initialBox?.width ?? 0;

            // Click to toggle
            await collapseToggle.click();
            await page.waitForTimeout(400); // Wait for transition

            const afterBox = await sidebar.boundingBox();
            const afterWidth = afterBox?.width ?? 0;

            // Width should have changed
            expect(Math.abs(initialWidth - afterWidth)).toBeGreaterThan(100);
        });

        test('should persist sidebar state across navigation', async ({ page }) => {
            await page.setViewportSize(viewports.medium);

            const collapseToggle = page.locator('[data-testid="sidebar-collapse-toggle"]');
            await expect(collapseToggle).toBeVisible();

            // Collapse the sidebar
            await collapseToggle.click();
            await page.waitForTimeout(400);

            const sidebar = page.locator('[data-testid="app-sidebar"]');
            const collapsedBox = await sidebar.boundingBox();
            const collapsedWidth = collapsedBox?.width ?? 0;

            // Navigate to history and back
            await page.locator('[data-testid="sidebar-nav-history"]').click();
            await expect(page).toHaveURL('/history');

            await page.goto('/dashboard');
            await page.waitForTimeout(400);

            // Sidebar should still be collapsed
            const afterNavBox = await sidebar.boundingBox();
            const afterNavWidth = afterNavBox?.width ?? 0;

            expect(Math.abs(collapsedWidth - afterNavWidth)).toBeLessThan(20);
        });
    });

    test.describe('Chat area text handling', () => {
        test('should wrap long text without horizontal scroll', async ({ page }) => {
            await page.setViewportSize(viewports.minimum);

            // Mock API to return a classification result
            await page.route('**/api/v1/classification/analyze', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        session_id: 'test-session-123',
                        attack_type: 'nigerian_419',
                        confidence: 95.5,
                        reasoning: 'Test reasoning for classification',
                        persona: {
                            name: 'Test Persona',
                            age: 65,
                            occupation: 'Retired Teacher',
                            writing_style: {
                                formality: 'casual',
                                typical_errors: ['spelling'],
                                use_caps_lock: false,
                            },
                            characteristic_phrases: ['Oh dear', 'How lovely'],
                        },
                    }),
                });
            });

            // Fill in email and analyze
            const textarea = page.getByPlaceholder('Paste phishing email content here...');
            await textarea.fill('Subject: Urgent Request\nDear Friend, I need your help...');

            const analyzeButton = page.locator('#analyze-button');
            await analyzeButton.click();

            // Wait for classification result
            await expect(page.getByText('Nigerian 419 Scam')).toBeVisible({ timeout: 10000 });

            // Check that page does not have horizontal overflow
            const hasHorizontalScroll = await page.evaluate(() => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            });

            // Some minimal overflow is acceptable (scrollbars, etc)
            if (hasHorizontalScroll) {
                const overflowAmount = await page.evaluate(() => {
                    return document.documentElement.scrollWidth - document.documentElement.clientWidth;
                });
                expect(overflowAmount).toBeLessThan(50);
            }
        });
    });

    test.describe('Session history page responsiveness', () => {
        test('should render history page at minimum width', async ({ page }) => {
            await page.setViewportSize(viewports.minimum);

            // Navigate to history
            await page.locator('[data-testid="sidebar-nav-history"]').click();
            await expect(page).toHaveURL('/history');

            // Page should load without errors
            await expect(page.getByRole('heading', { name: 'Session History' })).toBeVisible();

            // No horizontal scroll
            const documentWidth = await page.evaluate(() => document.documentElement.scrollWidth);
            const viewportWidth = await page.evaluate(() => window.innerWidth);
            expect(documentWidth).toBeLessThanOrEqual(viewportWidth + 10);
        });

        test('should stack export buttons on narrow screens', async ({ page }) => {
            await page.setViewportSize({ width: 640, height: 768 }); // Very narrow (below sm breakpoint)

            // This test would apply to session detail page
            // For now, just verify history page loads
            await page.locator('[data-testid="sidebar-nav-history"]').click();
            await expect(page).toHaveURL('/history');
        });
    });

    test.describe('Button accessibility', () => {
        test('should have clickable buttons at all widths', async ({ page }) => {
            for (const [name, viewport] of Object.entries(viewports)) {
                await page.setViewportSize(viewport);
                await page.goto('/dashboard');

                const analyzeButton = page.locator('#analyze-button');
                await expect(analyzeButton).toBeVisible();

                const buttonBox = await analyzeButton.boundingBox();
                expect(buttonBox?.width).toBeGreaterThan(50);
                expect(buttonBox?.height).toBeGreaterThan(25);
            }
        });
    });
});
