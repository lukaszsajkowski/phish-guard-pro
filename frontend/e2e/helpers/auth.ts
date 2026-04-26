import type { Page } from '@playwright/test';

export async function waitForStoredAuth(page: Page) {
    await page.waitForFunction(() =>
        Object.values(window.localStorage).some((value) =>
            typeof value === 'string' && value.includes('access_token')
        )
    );
    await page.waitForTimeout(250);
}
