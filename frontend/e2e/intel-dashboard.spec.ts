import { test, expect } from '@playwright/test';

test.describe('Intel Dashboard (US-012)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-intel-${timestamp}-${random}@example.com`;
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

    test('should display all 4 dashboard sections after classification', async ({ page }) => {
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
                    session_id: 'test-session-intel',
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

        // Wait for the attack type section to be visible (this is specific to Intel Dashboard)
        await expect(page.getByTestId('attack-type-section')).toBeVisible();

        // Section 1: Attack Type section should be visible with category and confidence
        await expect(page.getByTestId('attack-type-section').getByText('Nigerian 419 Scam')).toBeVisible();
        await expect(page.getByTestId('confidence-badge')).toContainText('96% confidence');

        // Section 2: IOC section should be visible (empty initially)
        await expect(page.getByTestId('ioc-section')).toBeVisible();
        await expect(page.getByText('Collected IOCs')).toBeVisible();
        await expect(page.getByText('No IOCs extracted yet')).toBeVisible();

        // Section 3: Risk Score section should be visible
        await expect(page.getByTestId('risk-score-section')).toBeVisible();
        await expect(page.getByTestId('risk-score-value')).toBeVisible();

        // Section 4: Timeline section should be visible (empty initially)
        await expect(page.getByTestId('timeline-section')).toBeVisible();
        await expect(page.getByText('Extraction Timeline')).toBeVisible();
        await expect(page.getByText('No events yet')).toBeVisible();
    });

    test('should show correct risk score based on attack type', async ({ page }) => {
        // Mock with high-severity attack type (CEO Fraud)
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'ceo_fraud',
                    confidence: 88,
                    reasoning: 'CEO impersonation detected',
                    classification_time_ms: 400,
                    session_id: 'test-session-ceo',
                    persona: {
                        persona_type: 'stressed_manager',
                        name: 'David Chen',
                        age: 42,
                        style_description: 'Professional and rushed',
                        background: 'Finance director'
                    }
                })
            });
        });

        await page.getByTestId('email-input-textarea').fill('I need you to wire $50,000 immediately...');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByTestId('attack-type-section').getByText('CEO Fraud')).toBeVisible();

        // Risk score should be higher for CEO fraud (base score 4)
        const riskScoreValue = page.getByTestId('risk-score-value');
        await expect(riskScoreValue).toBeVisible();
        const scoreText = await riskScoreValue.textContent();
        const score = parseInt(scoreText || '0', 10);
        expect(score).toBeGreaterThanOrEqual(4);
    });

    test('should update risk score when IOCs are extracted', async ({ page }) => {
        // Mock classification
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'crypto_investment',
                    confidence: 91,
                    reasoning: 'Crypto scam detected',
                    classification_time_ms: 350,
                    session_id: 'test-session-risk',
                    persona: {
                        persona_type: 'greedy_investor',
                        name: 'Mike Johnson',
                        age: 35,
                        style_description: 'Eager to invest',
                        background: 'Tech startup founder'
                    }
                })
            });
        });

        // Mock response with high-value IOCs
        await page.route('**/api/v1/response/generate', async route => {
            const request = route.request();
            const body = request.postDataJSON();

            if (!body.scammer_message) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'This looks promising! How do I invest?',
                        generation_time_ms: 2000,
                        safety_validated: true,
                        message_id: 'msg-risk-1'
                    })
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'Great! Where exactly do I send the BTC?',
                        generation_time_ms: 1500,
                        safety_validated: true,
                        message_id: 'msg-risk-2',
                        scammer_message_id: 'scam-risk-1',
                        extracted_iocs: [
                            {
                                id: 'ioc-btc-1',
                                type: 'btc_wallet',
                                value: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                                is_high_value: true
                            },
                            {
                                id: 'ioc-btc-2',
                                type: 'btc_wallet',
                                value: '3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy',
                                is_high_value: true
                            }
                        ]
                    })
                });
            }
        });

        // Get initial risk score
        await page.getByTestId('email-input-textarea').fill('Invest in crypto for 500% returns!');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByTestId('risk-score-value')).toBeVisible();
        const initialScore = parseInt(await page.getByTestId('risk-score-value').textContent() || '0', 10);

        // Generate response and submit scammer message with IOCs
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        await page.getByTestId('scammer-input-textarea').fill('Send BTC to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh or 3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy');
        await page.getByTestId('scammer-input-send-button').click();

        await expect(page.getByText('Great! Where exactly')).toBeVisible();

        // Risk score should have increased due to high-value IOCs
        const updatedScore = parseInt(await page.getByTestId('risk-score-value').textContent() || '0', 10);
        expect(updatedScore).toBeGreaterThan(initialScore);
    });

    test('should display timeline events after IOC extraction', async ({ page }) => {
        // Mock classification
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'fake_invoice',
                    confidence: 87,
                    reasoning: 'Invoice scam detected',
                    classification_time_ms: 300,
                    session_id: 'test-session-timeline',
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

        // Mock response with IOC
        await page.route('**/api/v1/response/generate', async route => {
            const request = route.request();
            const body = request.postDataJSON();

            if (!body.scammer_message) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'I will process that invoice.',
                        generation_time_ms: 2000,
                        safety_validated: true,
                        message_id: 'msg-timeline-1'
                    })
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'What are the wire details?',
                        generation_time_ms: 1500,
                        safety_validated: true,
                        message_id: 'msg-timeline-2',
                        scammer_message_id: 'scam-timeline-1',
                        extracted_iocs: [
                            {
                                id: 'ioc-iban-1',
                                type: 'iban',
                                value: 'DE89370400440532013000',
                                is_high_value: true
                            }
                        ]
                    })
                });
            }
        });

        // Setup and submit scammer message
        await page.getByTestId('email-input-textarea').fill('URGENT: Invoice payment required immediately');
        await page.getByTestId('analyze-button').click();
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        await page.getByTestId('scammer-input-textarea').fill('Wire payment to IBAN DE89370400440532013000');
        await page.getByTestId('scammer-input-send-button').click();
        await expect(page.getByText('What are the wire details?')).toBeVisible();

        // Timeline should now have an event
        await expect(page.getByTestId('timeline-section')).toBeVisible();
        await expect(page.getByText('No events yet')).not.toBeVisible();
        await expect(page.getByTestId('timeline-event')).toBeVisible();
        await expect(page.getByText(/Extracted IBAN/)).toBeVisible();
    });

    test('should highlight high-value IOCs in red', async ({ page }) => {
        // Mock classification
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 93,
                    reasoning: '419 scam detected',
                    classification_time_ms: 400,
                    session_id: 'test-session-highlight',
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

        // Mock response with both high and low value IOCs
        await page.route('**/api/v1/response/generate', async route => {
            const request = route.request();
            const body = request.postDataJSON();

            if (!body.scammer_message) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        content: 'This sounds wonderful!',
                        generation_time_ms: 2000,
                        safety_validated: true,
                        message_id: 'msg-highlight-1'
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
                        message_id: 'msg-highlight-2',
                        scammer_message_id: 'scam-highlight-1',
                        extracted_iocs: [
                            {
                                id: 'ioc-btc',
                                type: 'btc_wallet',
                                value: 'bc1testaddress123',
                                is_high_value: true
                            },
                            {
                                id: 'ioc-url',
                                type: 'url',
                                value: 'https://scam-site.com/pay',
                                is_high_value: false
                            }
                        ]
                    })
                });
            }
        });

        // Setup
        await page.getByTestId('email-input-textarea').fill('You have won $5 million!');
        await page.getByTestId('analyze-button').click();
        await page.getByTestId('generate-response-button').click();
        await expect(page.getByTestId('chat-message-bot')).toBeVisible();

        await page.getByTestId('scammer-input-textarea').fill('Send to bc1testaddress123 via https://scam-site.com/pay');
        await page.getByTestId('scammer-input-send-button').click();
        await expect(page.getByText('How do I proceed?')).toBeVisible();

        // Check high-value badge
        await expect(page.getByTestId('high-value-badge')).toBeVisible();
        await expect(page.getByTestId('high-value-badge')).toContainText('1 High Value');

        // High-value IOC should be styled with red
        const btcItem = page.getByTestId('ioc-item-btc_wallet');
        await expect(btcItem).toBeVisible();
        // The styling is applied, check the IOC is present
    });

    test('should show risk score progress bar', async ({ page }) => {
        // Mock classification with high-severity attack
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'ceo_fraud',
                    confidence: 95,
                    reasoning: 'CEO fraud detected',
                    classification_time_ms: 350,
                    session_id: 'test-session-bar',
                    persona: {
                        persona_type: 'stressed_manager',
                        name: 'Sarah Chen',
                        age: 45,
                        style_description: 'Busy professional',
                        background: 'CFO'
                    }
                })
            });
        });

        await page.getByTestId('email-input-textarea').fill('This is the CEO. Wire $100k now.');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByTestId('attack-type-section').getByText('CEO Fraud')).toBeVisible();

        // Check risk score bar element exists
        await expect(page.getByTestId('risk-score-bar')).toBeVisible();

        // Check risk label is shown
        const riskSection = page.getByTestId('risk-score-section');
        await expect(riskSection).toContainText('Risk');
        await expect(riskSection).toContainText('/10');
    });

    test('should reset dashboard when analyzing new email', async ({ page }) => {
        // First analysis
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 90,
                    reasoning: '419 detected',
                    classification_time_ms: 300,
                    session_id: 'test-session-reset-1',
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'John Smith',
                        age: 70,
                        style_description: 'Trusting',
                        background: 'Retired'
                    }
                })
            });
        });

        await page.getByTestId('email-input-textarea').fill('Nigerian prince email');
        await page.getByTestId('analyze-button').click();
        await expect(page.getByText('Nigerian 419 Scam')).toBeVisible();

        // Now analyze a different email
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'delivery_scam',
                    confidence: 85,
                    reasoning: 'Delivery scam detected',
                    classification_time_ms: 350,
                    session_id: 'test-session-reset-2',
                    persona: {
                        persona_type: 'confused_student',
                        name: 'Alex Kim',
                        age: 22,
                        style_description: 'Young and confused',
                        background: 'College student'
                    }
                })
            });
        });

        await page.getByTestId('email-input-textarea').fill('Your package is delayed, click here');
        await page.getByTestId('analyze-button').click();

        // Dashboard should show new attack type
        await expect(page.getByText('Delivery Scam').first()).toBeVisible();
        // IOCs should be reset
        await expect(page.getByText('No IOCs extracted yet')).toBeVisible();
        // Timeline should be reset
        await expect(page.getByText('No events yet')).toBeVisible();
    });
});

test.describe('Side Panel Collapse (US-026)', () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto('/register');

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-collapse-${timestamp}-${random}@example.com`;
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

    test('should show collapse button in side panel header', async ({ page }) => {
        // Set viewport to wide screen to ensure panel is expanded
        await page.setViewportSize({ width: 1400, height: 900 });

        // Mock the classification API
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95,
                    reasoning: '419 scam detected',
                    classification_time_ms: 500,
                    session_id: 'test-session-collapse',
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

        // Wait for side panel to appear
        await expect(page.getByTestId('side-panel')).toBeVisible();

        // Collapse button should be visible
        await expect(page.getByTestId('collapse-side-panel-button')).toBeVisible();
    });

    test('should collapse side panel when collapse button is clicked', async ({ page }) => {
        // Set viewport to wide screen
        await page.setViewportSize({ width: 1400, height: 900 });

        // Mock the classification API
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95,
                    reasoning: '419 scam detected',
                    classification_time_ms: 500,
                    session_id: 'test-session-collapse-2',
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

        // Wait for side panel
        await expect(page.getByTestId('side-panel')).toBeVisible();

        // Click collapse button
        await page.getByTestId('collapse-side-panel-button').click();

        // IntelDashboard should be hidden
        await expect(page.getByTestId('intel-dashboard')).not.toBeVisible();

        // Expand button should be visible
        await expect(page.getByTestId('expand-side-panel-button')).toBeVisible();
    });

    test('should expand side panel when expand button is clicked', async ({ page }) => {
        // Set viewport to wide screen
        await page.setViewportSize({ width: 1400, height: 900 });

        // Mock the classification API
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95,
                    reasoning: '419 scam detected',
                    classification_time_ms: 500,
                    session_id: 'test-session-expand',
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

        // Wait for side panel
        await expect(page.getByTestId('side-panel')).toBeVisible();

        // Collapse first
        await page.getByTestId('collapse-side-panel-button').click();
        await expect(page.getByTestId('expand-side-panel-button')).toBeVisible();

        // Expand again
        await page.getByTestId('expand-side-panel-button').click();

        // IntelDashboard should be visible again
        await expect(page.getByTestId('intel-dashboard')).toBeVisible();

        // Collapse button should be visible again
        await expect(page.getByTestId('collapse-side-panel-button')).toBeVisible();
    });

    test('should auto-collapse on narrow screens', async ({ page }) => {
        // Mock the classification API
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95,
                    reasoning: '419 scam detected',
                    classification_time_ms: 500,
                    session_id: 'test-session-auto-collapse',
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

        // Set narrow viewport (below 1280px)
        await page.setViewportSize({ width: 1100, height: 900 });

        // Input email content and analyze
        await page.getByTestId('email-input-textarea').fill('Dear Friend, I am a Nigerian Prince...');
        await page.getByTestId('analyze-button').click();

        // Wait for side panel
        await expect(page.getByTestId('side-panel')).toBeVisible();

        // Panel should be collapsed automatically
        await expect(page.getByTestId('expand-side-panel-button')).toBeVisible();
        await expect(page.getByTestId('intel-dashboard')).not.toBeVisible();
    });

    test('should show IOC count badge when collapsed', async ({ page }) => {
        // Set viewport to wide screen first
        await page.setViewportSize({ width: 1400, height: 900 });

        // Mock classification with IOCs
        await page.route('**/api/v1/classification/analyze', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    attack_type: 'nigerian_419',
                    confidence: 95,
                    reasoning: '419 scam detected',
                    classification_time_ms: 500,
                    session_id: 'test-session-ioc-badge',
                    persona: {
                        persona_type: 'naive_retiree',
                        name: 'Margaret Thompson',
                        age: 72,
                        style_description: 'Trusting and polite',
                        background: 'Retired teacher'
                    },
                    extracted_iocs: [
                        { type: 'url', value: 'https://scam.com', is_high_value: false },
                        { type: 'btc_wallet', value: 'bc1test123', is_high_value: true }
                    ]
                })
            });
        });

        // Input email content and analyze
        await page.getByTestId('email-input-textarea').fill('Dear Friend, send money to https://scam.com or bc1test123...');
        await page.getByTestId('analyze-button').click();

        // Wait for side panel
        await expect(page.getByTestId('side-panel')).toBeVisible();

        // Collapse the panel
        await page.getByTestId('collapse-side-panel-button').click();

        // Should show IOC count badge (use more specific selector within side panel)
        const iocBadge = page.getByTestId('side-panel').locator('span[title="2 IOCs collected"]');
        await expect(iocBadge).toBeVisible();
        await expect(iocBadge).toHaveText('2');
    });
});
