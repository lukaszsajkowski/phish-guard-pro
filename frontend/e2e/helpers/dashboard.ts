import { expect, type Page } from '@playwright/test';

export async function waitForAnalysisResult(page: Page) {
    await expect(page.getByTestId('generate-response-button')).toBeVisible({ timeout: 10000 });
}

export async function expandIntelPanel(page: Page) {
    const expandButton = page.getByTestId('expand-side-panel-button');

    await expect(page.getByTestId('side-panel')).toBeVisible({ timeout: 10000 });

    try {
        await expect(expandButton).toBeVisible({ timeout: 1000 });
        await expandButton.evaluate((button: HTMLElement) => button.click());
    } catch {
        // Already expanded on desktop.
    }
}

export async function waitForIntelDashboard(page: Page) {
    await expandIntelPanel(page);
    await expect(page.getByTestId('intel-dashboard')).toBeVisible({ timeout: 10000 });
}
