import { test, expect } from "./fixtures";

test.describe("Guest Flow", () => {
  test("landing page loads", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("text=Discover your scent")).toBeVisible();
    await expect(page.locator("text=Free Experience")).toBeVisible();
    await expect(page.locator("text=情绪人格 × 香水 AI Agent")).toBeVisible();
  });

  test("card selection and SSE generation", async ({ page }) => {
    await page.goto("/guest");
    await expect(page.locator("text=Pick a Card")).toBeVisible();

    // Click two emotion cards
    await page.locator("[data-emotion-id='joy']").click();
    await page.locator("[data-emotion-id='calm']").click();

    // Start
    const startButton = page.locator("button:has-text('Start Exploring')");
    await expect(startButton).toBeEnabled();
    await startButton.click();

    // Wait for emotion confirmation
    await expect(page.locator("text=I sense you're feeling")).toBeVisible({
      timeout: 15000,
    });

    // Wait for generation to complete (fragrance cards + template copy)
    await expect(page.locator("text=New Session")).toBeVisible({
      timeout: 30000,
    });
  });

  test("text input mode switches and submits", async ({ page }) => {
    await page.goto("/guest");
    await page.locator("text=Write how you feel").click();

    const textarea = page.locator("textarea");
    await expect(textarea).toBeVisible();
    await textarea.fill("I feel very happy and excited today");

    await page.locator("button:has-text('Start Exploring')").click();
    // Text-based emotion resolution goes through LLM→keyword→default chain.
    // In CI (no LLM key) the keyword fallback is fast but the async pipeline
    // adds latency; use a generous timeout.
    await expect(page.locator("text=I sense you're feeling")).toBeVisible({
      timeout: 25000,
    });
  });

  test("emotion correction returns to initial state", async ({ page }) => {
    await page.goto("/guest");
    await page.locator("[data-emotion-id='joy']").click();
    await page.locator("button:has-text('Start Exploring')").click();

    const correctButton = page.locator("text=Not right? Pick again");
    await expect(correctButton).toBeVisible({ timeout: 15000 });
    await correctButton.click();

    // Back to card selection
    await expect(page.locator("text=Pick a Card")).toBeVisible();
    await expect(page.locator("text=Start Exploring")).toBeVisible();
  });

  test("settings page saves API key", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.locator("text=LLM API Key")).toBeVisible();

    await page.locator("input[type='password']").fill("sk-test-key-123");
    await page.locator("button:has-text('Save Key')").click();

    await expect(page.locator("text=API key saved successfully")).toBeVisible({
      timeout: 10000,
    });
  });

  test("complete phase shows Share and Save Note buttons", async ({ page }) => {
    await page.goto("/guest");
    await page.locator("[data-emotion-id='joy']").click();
    await page.locator("button:has-text('Start Exploring')").click();

    // Wait for "Share" button directly (only appears when generation reaches
    // "complete" phase). Don't wait for "New Session" first — the nav bar also
    // contains that text and would give a false-positive too early.
    // Multiple Share buttons exist (3 per card in ActionBar + 1 bottom bar).
    // Use .first() to avoid Playwright strict-mode and just verify visibility.
    await expect(page.locator("text=Share").first()).toBeVisible({
      timeout: 30000,
    });
    await expect(page.locator("text=Save as Note")).toBeVisible();
  });

  test("share page renders recommendation", async ({ page }) => {
    const shareId = process.env.TEST_SHARE_ID;
    test.skip(!shareId, "TEST_SHARE_ID env var not set");

    await page.goto(`/s/${shareId}`);
    await expect(page.locator("text=Perfume AI")).toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator("text=Experience your own")).toBeVisible();
  });

  test("invalid input blocked by frontend validation", async ({ page }) => {
    await page.goto("/guest");

    // Start disabled with no cards and no text
    const startButton = page.locator("button:has-text('Start Exploring')");
    await expect(startButton).toBeDisabled();

    // Switch to text mode, still disabled with empty input
    await page.locator("text=Write how you feel").click();
    await expect(startButton).toBeDisabled();

    // Type something — enables
    await page.locator("textarea").fill("Hi");
    await expect(startButton).toBeEnabled();

    // Clear — disables again
    await page.locator("textarea").fill("");
    await expect(startButton).toBeDisabled();
  });
});
