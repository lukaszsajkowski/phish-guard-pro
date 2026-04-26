import { test, expect } from '@playwright/test';
import { waitForAnalysisResult, waitForIntelDashboard } from './helpers/dashboard';

test.describe('IOC Extraction (US-011)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-ioc-${timestamp}-${random}@example.com`;
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

    test('should display Intel Dashboard in side panel', async ({ page }) => {
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
                    session_id: 'test-session-ioc',
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

        // Input email content and analyze
        await page.getByTestId('email-input-textarea').fill('Dear Friend, I am a Nigerian Prince...');
        await page.getByTestId('analyze-button').click();
        await waitForIntelDashboard(page);

        // Intel Dashboard should be visible in side panel
        await expect(page.getByTestId('intel-dashboard')).toBeVisible();
        await expect(page.getByText('Threat Intel')).toBeVisible();
        await expect(page.getByText('No IOCs extracted yet')).toBeVisible();
    });

    test('should display extracted IOCs after scammer message with BTC wallet', async ({ page }) => {
        // Mock the classification API
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'crypto_investment',
                    confidence: 92,
                    reasoning: 'Crypto scam detected',
                    classification_time_ms: 400,
                    session_id: 'test-session-btc',
                    persona: {
                        persona_type: 'greedy_investor',
                        name: 'Robert Chen',
                        age: 45,
                        style_description: 'Eager and quick',
                        background: 'Day trader'
                    }
                })
            });
        });

        // Mock response generation with IOCs
        await page.route('**/api/v1/response/generate', async route => {
            const request = route.request();
            const body = request.postDataJSON();

            if (!body.scammer_message) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'Interesting! Tell me more about this investment.',
                        generation_time_ms: 2000,
                        safety_validated: true,
                        regeneration_count: 0,
                        message_id: 'msg-btc-1'
                    })
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'How do I start? Where do I send the money?',
                        generation_time_ms: 1500,
                        safety_validated: true,
                        regeneration_count: 0,
                        message_id: 'msg-btc-2',
                        scammer_message_id: 'scam-btc-1',
                        extracted_iocs: [
                            {
                                type: 'btc_wallet',
                                value: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                                context: '...send to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh immediately...',
                                is_high_value: true
                            }
                        ]
                    })
                });
            }
        });

        // Setup
        await page.getByTestId('email-input-textarea').fill('Invest in crypto for guaranteed 500% returns!');
        await page.getByTestId('analyze-button').click();
        await waitForAnalysisResult(page);

        // Generate first response
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Submit scammer message with BTC wallet
        await page.getByTestId('scammer-input-textarea').fill('Send money to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh');
        await page.getByTestId('scammer-input-send-button').click();

        // Wait for bot response
        await expect(page.getByText('How do I start?')).toBeVisible();
        await waitForIntelDashboard(page);

        // IOC should appear in Intel Dashboard
        const btcIocItem = page.getByTestId('ioc-item-btc_wallet');
        await expect(btcIocItem).toBeVisible();
        await expect(btcIocItem.getByText('bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')).toBeVisible();
        await expect(page.getByTestId('high-value-badge')).toBeVisible();
    });

    test('should display multiple IOC types', async ({ page }) => {
        // Mock APIs
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'fake_invoice',
                    confidence: 88,
                    reasoning: 'Invoice scam detected',
                    classification_time_ms: 350,
                    session_id: 'test-session-multi-ioc',
                    persona: {
                        persona_type: 'stressed_manager',
                        name: 'Jennifer Walsh',
                        age: 38,
                        style_description: 'Professional',
                        background: 'Office manager'
                    }
                })
            });
        });

        await page.route('**/api/v1/response/generate', async route => {
            const request = route.request();
            const body = request.postDataJSON();

            if (!body.scammer_message) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'I will process that payment.',
                        generation_time_ms: 2000,
                        safety_validated: true,
                        regeneration_count: 0,
                        message_id: 'msg-multi-1'
                    })
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'What are the wire details?',
                        generation_time_ms: 1800,
                        safety_validated: true,
                        regeneration_count: 0,
                        message_id: 'msg-multi-2',
                        scammer_message_id: 'scam-multi-1',
                        extracted_iocs: [
                            {
                                type: 'iban',
                                value: 'DE89370400440532013000',
                                context: '...wire to IBAN DE89370400440532013000...',
                                is_high_value: true
                            },
                            {
                                type: 'phone',
                                value: '+44 20 7123 4567',
                                context: '...call +44 20 7123 4567...',
                                is_high_value: false
                            },
                            {
                                type: 'url',
                                value: 'https://fake-invoice.com/pay',
                                context: '...visit https://fake-invoice.com/pay...',
                                is_high_value: false
                            }
                        ]
                    })
                });
            }
        });

        // Setup and generate first response
        await page.getByTestId('email-input-textarea').fill('URGENT: Invoice payment required');
        await page.getByTestId('analyze-button').click();
        await waitForAnalysisResult(page);
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Submit scammer message with multiple IOCs
        await page.getByTestId('scammer-input-textarea').fill('Wire to IBAN DE89370400440532013000, or call +44 20 7123 4567, or visit https://fake-invoice.com/pay');
        await page.getByTestId('scammer-input-send-button').click();

        // Wait for response
        await expect(page.getByText('What are the wire details?')).toBeVisible();
        await waitForIntelDashboard(page);

        // Check all IOC types are displayed
        await expect(page.getByTestId('ioc-item-iban')).toBeVisible();
        await expect(page.getByTestId('ioc-item-phone')).toBeVisible();
        await expect(page.getByTestId('ioc-item-url')).toBeVisible();

        // High-value badge should show count
        await expect(page.getByTestId('high-value-badge')).toContainText('1 High Value');
    });

    test('should show IOC count in dashboard', async ({ page }) => {
        // Mock APIs
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 90,
                    reasoning: '419 detected',
                    classification_time_ms: 300,
                    session_id: 'test-session-count',
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'Betty Wilson',
                        age: 68,
                        style_description: 'Trusting',
                        background: 'Retired nurse'
                    }
                })
            });
        });

        await page.route('**/api/v1/response/generate', async route => {
            const request = route.request();
            const body = request.postDataJSON();

            if (!body.scammer_message) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'This sounds wonderful!',
                        generation_time_ms: 1500,
                        safety_validated: true,
                        message_id: 'msg-count-1'
                    })
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'How do I proceed?',
                        generation_time_ms: 1500,
                        safety_validated: true,
                        message_id: 'msg-count-2',
                        scammer_message_id: 'scam-count-1',
                        extracted_iocs: [
                            { type: 'btc_wallet', value: 'bc1abc...', is_high_value: true },
                            { type: 'iban', value: 'GB82WEST...', is_high_value: true },
                        ]
                    })
                });
            }
        });

        // Setup
        await page.getByTestId('email-input-textarea').fill('You won $1 million!');
        await page.getByTestId('analyze-button').click();
        await waitForAnalysisResult(page);
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        // Submit scammer message
        await page.getByTestId('scammer-input-textarea').fill('Send BTC to bc1abc... or wire to IBAN GB82WEST...');
        await page.getByTestId('scammer-input-send-button').click();

        // Wait for response
        await expect(page.getByText('How do I proceed?')).toBeVisible();
        await waitForIntelDashboard(page);

        // Check count display
        await expect(page.getByText('2 IOCs')).toBeVisible();
        await expect(page.getByTestId('high-value-badge')).toContainText('2 High Value');
    });
});
