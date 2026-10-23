import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

/*
 * Runs against a backend started with LLM_PROVIDER=fake (as in CI): the stand-in model quotes
 * the top passage and marks its answer "(إجابة تجريبية)". Retrieval, citation validation,
 * saving and the PDF viewer are all real.
 */
const SAMPLE_PDF = path.join(__dirname, "../../samples/daleel-sample-guide.pdf");

async function registerWithReadyDocument(page: Page) {
  await page.goto("/register");
  await page.getByLabel("الاسم").fill("جنى");
  await page.getByLabel("البريد الإلكتروني").fill(`chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`);
  await page.getByLabel("كلمة المرور").fill("s3cure-pass");
  await page.getByRole("button", { name: "إنشاء الحساب" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.getByTestId("file-input").setInputFiles(SAMPLE_PDF);
  await expect(page.getByText("جاهز", { exact: true })).toBeVisible({ timeout: 60_000 });
}

test("chat asks for a document first when none is ready", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("الاسم").fill("جنى");
  await page.getByLabel("البريد الإلكتروني").fill(`empty-${Date.now()}@example.com`);
  await page.getByLabel("كلمة المرور").fill("s3cure-pass");
  await page.getByRole("button", { name: "إنشاء الحساب" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.getByRole("link", { name: "اسأل" }).click();
  await expect(page.getByText("ما فيه وثائق جاهزة")).toBeVisible();
  await expect(page.getByLabel("سؤالك")).toBeDisabled();
});

test("ask a question, open the cited page, and find the conversation again", async ({ page }) => {
  await registerWithReadyDocument(page);
  await page.goto("/chat");

  await page.getByLabel("سؤالك").fill("كم نسبة الغياب اللي تحرمني من الاختبار؟");
  await page.keyboard.press("Enter");

  // The answer cites the attendance rule on page 3 (found thanks to hybrid search).
  await expect(page.getByText("(إجابة تجريبية)")).toBeVisible({ timeout: 30_000 });
  await expect(page).toHaveURL(/\/chat\?c=/);
  const sources = page.getByRole("list", { name: "المصادر" });
  await expect(sources.getByText("صفحة 3")).toBeVisible();
  await expect(sources.getByText(/25 بالمئة/)).toBeVisible();

  // Clicking the citation opens the page with the passage highlighted.
  await page.getByRole("button", { name: /^المصدر 1:/ }).click();
  const viewer = page.getByRole("dialog");
  await expect(viewer.getByRole("heading", { name: /دليل الطالب/ })).toBeVisible();
  await expect(viewer.getByTestId("highlight").first()).toBeVisible({ timeout: 20_000 });
  await page.keyboard.press("Escape");
  await expect(viewer).toBeHidden();

  // The conversation is saved and survives a reload.
  await page.reload();
  await expect(page.getByText("(إجابة تجريبية)")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "كم نسبة الغياب اللي تحرمني من الاختبار؟" })).toBeVisible();
});
