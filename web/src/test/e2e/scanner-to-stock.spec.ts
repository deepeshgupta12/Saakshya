/* E2E: pick a stock from scanner → land on stock detail → assert evidence + no levels.
   Requires the dev server + M5 API running at localhost:8000.
   docs/steps/06 exit gate, SPEC §12 M6. */

import { test, expect } from "@playwright/test";

test.describe("M6 E2E — scanner to stock detail", () => {
  test("momentum scanner loads and navigates to stock detail", async ({ page }) => {
    await page.goto("/scanners/momentum");

    /* Page must load without errors */
    await expect(page).toHaveTitle(/momentum scanner/i);

    /* NotAdviceBanner must be visible */
    await expect(page.getByText(/not investment advice/i).first()).toBeVisible();

    /* If there are scanner results, click the first stock */
    const firstSymbol = page.locator("table tbody tr:first-child td:first-child a").first();
    const hasResults = await firstSymbol.isVisible().catch(() => false);

    if (hasResults) {
      const symbol = await firstSymbol.textContent();
      await firstSymbol.click();

      /* On stock detail */
      await expect(page).toHaveURL(new RegExp(`/stocks/${symbol}`));

      /* Must show scanner membership chip or score */
      await expect(page.getByText(/appears in scanners|scanner/i).first()).toBeVisible();

      /* Must NOT have entry / target / stop-loss elements */
      await expect(page.getByText(/^entry point$/i)).not.toBeVisible();
      await expect(page.getByText(/^stop loss$/i)).not.toBeVisible();
      await expect(page.getByText(/^target price$/i)).not.toBeVisible();

      /* RA-gated placeholder must be present instead */
      await expect(page.getByText(/research analyst registration/i)).toBeVisible();

      /* Grounding badge must be present (if AI summary loaded) */
      const groundingBadge = page.getByText(/grounded in this stock/i);
      const suppressedNote = page.getByText(/ai summary unavailable/i);
      const hasGrounding = await groundingBadge.isVisible().catch(() => false);
      const hasSuppressed = await suppressedNote.isVisible().catch(() => false);
      expect(hasGrounding || hasSuppressed).toBeTruthy();

      /* NotAdviceBanner still visible */
      await expect(page.getByText(/not investment advice/i).first()).toBeVisible();
    }
  });

  test("reduce-motion: final values render immediately (no count-up animation)", async ({ browser }) => {
    const context = await browser.newContext({
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    await page.goto("/scanners/momentum");

    /* Score badges must show their numeric values immediately */
    const scoreBadges = page.locator('[aria-label*="Score"]');
    if (await scoreBadges.count() > 0) {
      await expect(scoreBadges.first()).toBeVisible();
      /* The value should be a number (count-up complete immediately) */
      const label = await scoreBadges.first().getAttribute("aria-label");
      expect(label).toMatch(/\d+/);
    }

    await context.close();
  });
});
