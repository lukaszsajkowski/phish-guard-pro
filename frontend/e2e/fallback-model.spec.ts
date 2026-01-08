import { test, expect } from "@playwright/test";

/**
 * E2E tests for US-023: Fallback to Cheaper Model
 *
 * Tests that the FallbackModelNotice component is displayed when
 * the backend returns used_fallback_model: true
 */

test.describe("Fallback Model Notice (US-023)", () => {
    test.beforeEach(async ({ page }) => {
        // Register and login
        await page.goto("/register");

        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        const email = `e2e-test-fallback-${timestamp}-${random}@example.com`;
        const password = "validPassword123";

        await page.locator("#email").fill(email);
        await page.locator("#password").fill(password);
        await page.locator("#confirm-password").fill(password);

        const registerButton = page.locator("#register-button");
        await expect(registerButton).toBeEnabled();
        await registerButton.click();

        await expect(page.locator("#registration-success-message")).toBeVisible();

        // Login
        await page.locator("#email").fill(email);
        await page.locator("#password").fill(password);
        await page.getByRole("button", { name: "Sign in" }).click();

        await expect(page).toHaveURL("/dashboard");
    });

    test("displays fallback notice when used_fallback_model is true", async ({
        page,
    }) => {
        // Mock classification API
        await page.route("**/api/v1/classification/analyze", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    attack_type: "nigerian_419",
                    confidence: 95.0,
                    reasoning: "Test classification",
                    session_id: "test-session-id",
                    persona: {
                        id: "test-persona",
                        name: "Helen",
                        age: 68,
                        persona_type: "elderly_trusting",
                        style_description: "Friendly and trusting elderly person",
                        background: "Retired teacher",
                    },
                }),
            });
        });

        // Mock response generation with fallback model used
        await page.route("**/api/v1/response/generate", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    content: "Test response from fallback model",
                    generation_time_ms: 1500,
                    safety_validated: true,
                    regeneration_count: 0,
                    used_fallback_model: true, // Fallback was used
                    message_id: "test-message-id",
                    turn_count: 1,
                    turn_limit: 20,
                    is_at_limit: false,
                    thinking: {
                        turn_goal: "Test goal",
                        selected_tactic: "building_trust",
                        reasoning: "Test reasoning",
                    },
                }),
            });
        });

        // Enter email and analyze
        const emailInput = page.getByTestId("email-input-textarea");
        await emailInput.fill(
            "Dear Friend, I am a Nigerian prince with $10M for you..."
        );
        await page.getByTestId("analyze-button").click();

        // Wait for classification and click generate
        await page
            .getByTestId("generate-response-button")
            .waitFor({ state: "visible" });
        await page.getByTestId("generate-response-button").click();

        // Verify fallback notice is displayed
        const fallbackNotice = page.getByTestId("fallback-model-notice");
        await expect(fallbackNotice).toBeVisible();
        await expect(fallbackNotice).toContainText("Using faster model");
    });

    test("does not display fallback notice when used_fallback_model is false", async ({
        page,
    }) => {
        // Mock classification API
        await page.route("**/api/v1/classification/analyze", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    attack_type: "nigerian_419",
                    confidence: 95.0,
                    reasoning: "Test classification",
                    session_id: "test-session-id",
                    persona: {
                        id: "test-persona",
                        name: "Helen",
                        age: 68,
                        persona_type: "elderly_trusting",
                        style_description: "Friendly and trusting elderly person",
                        background: "Retired teacher",
                    },
                }),
            });
        });

        // Mock response generation WITHOUT fallback
        await page.route("**/api/v1/response/generate", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    content: "Test response from primary model",
                    generation_time_ms: 1500,
                    safety_validated: true,
                    regeneration_count: 0,
                    used_fallback_model: false, // Primary model used
                    message_id: "test-message-id",
                    turn_count: 1,
                    turn_limit: 20,
                    is_at_limit: false,
                    thinking: {
                        turn_goal: "Test goal",
                        selected_tactic: "building_trust",
                        reasoning: "Test reasoning",
                    },
                }),
            });
        });

        // Enter email and analyze
        const emailInput = page.getByTestId("email-input-textarea");
        await emailInput.fill(
            "Dear Friend, I am a Nigerian prince with $10M for you..."
        );
        await page.getByTestId("analyze-button").click();

        // Wait for classification and click generate
        await page
            .getByTestId("generate-response-button")
            .waitFor({ state: "visible" });
        await page.getByTestId("generate-response-button").click();

        // Wait for message to appear
        await page.locator('[data-testid^="chat-message-"]').first().waitFor();

        // Verify fallback notice is NOT displayed
        const fallbackNotice = page.getByTestId("fallback-model-notice");
        await expect(fallbackNotice).not.toBeVisible();
    });
});
