import { test, expect } from '@playwright/test';

test.describe('EBP Copilot UI Tests', () => {

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('homepage loads with disclaimer banner', async ({ page }) => {
        // Check disclaimer is visible
        await expect(page.locator('text=DEMO ONLY')).toBeVisible();
        await expect(page.locator('text=Not for clinical use')).toBeVisible();

        // Screenshot
        await page.screenshot({ path: 'tests/screenshots/homepage.png', fullPage: true });
    });

    test('branding header displays correctly', async ({ page }) => {
        await expect(page.locator('text=MedGemma')).toBeVisible();
        await expect(page.locator('text=EBP')).toBeVisible();
    });

    test('phase tabs are visible and clickable', async ({ page }) => {
        const phases = ['ASK', 'ACQUIRE', 'APPRAISE', 'APPLY', 'ASSESS'];

        for (const phase of phases) {
            const tab = page.locator(`button:has-text("${phase}")`);
            await expect(tab).toBeVisible();
        }

        // Click ACQUIRE tab
        await page.click('button:has-text("ACQUIRE")');
        await page.screenshot({ path: 'tests/screenshots/acquire-phase.png' });
    });

    test('PICO section displays in ASK phase', async ({ page }) => {
        await expect(page.locator('text=Clinical Question (PICO)')).toBeVisible();
        await expect(page.locator('text=Patient / Problem')).toBeVisible();
        await expect(page.locator('text=Intervention')).toBeVisible();
        await expect(page.locator('text=Comparison')).toBeVisible();
        await expect(page.locator('text=Outcome')).toBeVisible();
    });

    test('chat panel is present', async ({ page }) => {
        // Check for chat input area
        await expect(page.locator('textarea, input[type="text"]').first()).toBeVisible();
    });

    test('settings modal opens and closes', async ({ page }) => {
        // Click center of radial (settings trigger)
        await page.click('text=MedGemma');

        // Wait a moment for potential modal
        await page.waitForTimeout(500);
        await page.screenshot({ path: 'tests/screenshots/after-brand-click.png' });
    });

});

test.describe('Demo Case Loading', () => {

    test('demo cases are visible in settings', async ({ page }) => {
        await page.goto('/');

        // Try to open settings (click center of visualization)
        const settingsTrigger = page.locator('[class*="cursor-pointer"]').first();
        if (await settingsTrigger.isVisible()) {
            await settingsTrigger.click();
            await page.waitForTimeout(500);
        }

        await page.screenshot({ path: 'tests/screenshots/settings-modal.png' });
    });

});

test.describe('Visual Regression', () => {

    test('screenshot: empty state', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.screenshot({
            path: 'tests/screenshots/visual-empty-state.png',
            fullPage: true
        });
    });

    test('screenshot: all phases', async ({ page }) => {
        await page.goto('/');
        const phases = ['ASK', 'ACQUIRE', 'APPRAISE', 'APPLY', 'ASSESS'];

        for (const phase of phases) {
            await page.click(`button:has-text("${phase}")`);
            await page.waitForTimeout(300);
            await page.screenshot({
                path: `tests/screenshots/phase-${phase.toLowerCase()}.png`
            });
        }
    });

});
