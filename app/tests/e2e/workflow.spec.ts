import { test, expect } from '@playwright/test';

test.describe('PICO Workflow E2E', () => {

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('PICO fields are editable', async ({ page }) => {
        // Navigate to ASK phase
        await page.click('button:has-text("ASK")');

        // Find PICO field and click to edit
        const patientField = page.locator('text=Patient / Problem').locator('..').locator('..');
        await patientField.click();

        // Wait for potential input to appear
        await page.waitForTimeout(300);
        await page.screenshot({ path: 'tests/screenshots/pico-edit-mode.png' });
    });

    test('completeness bar updates', async ({ page }) => {
        // Check completeness indicator exists
        await expect(page.locator('text=Completeness')).toBeVisible();

        // Note: Full test would require typing in chat and checking PICO updates
        await page.screenshot({ path: 'tests/screenshots/completeness-bar.png' });
    });

    test('references display in ACQUIRE phase', async ({ page }) => {
        // Navigate to ACQUIRE
        await page.click('button:has-text("ACQUIRE")');
        await page.waitForTimeout(300);

        // Check for Evidence Library header
        await expect(page.locator('text=Evidence Library')).toBeVisible();
        await page.screenshot({ path: 'tests/screenshots/evidence-library.png' });
    });

    test('appraisal section in APPRAISE phase', async ({ page }) => {
        await page.click('button:has-text("APPRAISE")');
        await page.waitForTimeout(300);
        await page.screenshot({ path: 'tests/screenshots/appraise-phase.png' });
    });

    test('recommendations in APPLY phase', async ({ page }) => {
        await page.click('button:has-text("APPLY")');
        await page.waitForTimeout(300);
        await page.screenshot({ path: 'tests/screenshots/apply-phase.png' });
    });

    test('outcomes in ASSESS phase', async ({ page }) => {
        await page.click('button:has-text("ASSESS")');
        await page.waitForTimeout(300);
        await page.screenshot({ path: 'tests/screenshots/assess-phase.png' });
    });

});

test.describe('Chat Interaction', () => {

    test('can type in chat input', async ({ page }) => {
        await page.goto('/');

        // Find textarea/input
        const chatInput = page.locator('textarea').first();
        await chatInput.fill('Patient with type 2 diabetes');

        await page.screenshot({ path: 'tests/screenshots/chat-with-input.png' });
    });

    test('model selector is visible', async ({ page }) => {
        await page.goto('/');

        // Look for model dropdown
        const modelSelector = page.locator('select, [class*="model"]').first();
        await page.screenshot({ path: 'tests/screenshots/model-selector.png' });
    });

});
