import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

const SAMPLE_PDF = path.join(__dirname, "../../samples/daleel-sample-guide.pdf");

async function registerFreshUser(page: Page) {
  await page.goto("/register");
  await page.getByLabel("الاسم").fill("جنى");
  await page.getByLabel("البريد الإلكتروني").fill(`docs-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`);
  await page.getByLabel("كلمة المرور").fill("s3cure-pass");
  await page.getByRole("button", { name: "إنشاء الحساب" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test("upload a PDF, wait until it is processed, open it, then delete it", async ({ page, browser }) => {
  await registerFreshUser(page);
  await expect(page.getByText("لا توجد وثائق بعد")).toBeVisible();

  await page.getByTestId("file-input").setInputFiles(SAMPLE_PDF);

  const row = page.getByRole("listitem").filter({ hasText: "دليل الطالب - جامعة الساحل" });
  await expect(row).toBeVisible();
  await expect(row.getByText("4 صفحات")).toBeVisible();
  // The worker extracts, chunks and embeds in the background; the list polls until it is ready.
  await expect(row.getByText("جاهز", { exact: true })).toBeVisible({ timeout: 60_000 });

  // The file opens for its owner only.
  const href = await row.getByRole("link", { name: "فتح الملف" }).getAttribute("href");
  const ownFile = await page.request.get(href!);
  expect(ownFile.status()).toBe(200);
  expect(ownFile.headers()["content-type"]).toBe("application/pdf");
  const anonymous = await (await browser.newContext()).request.get(new URL(href!, page.url()).toString());
  expect(anonymous.status()).toBe(401);

  await row.getByRole("button", { name: /^حذف/ }).click();
  await expect(page.getByRole("heading", { name: "حذف الوثيقة؟" })).toBeVisible();
  await page.getByRole("button", { name: "حذف نهائي" }).click();
  await expect(page.getByText("لا توجد وثائق بعد")).toBeVisible();
});

test("a file that is not really a PDF is rejected with a clear message", async ({ page }) => {
  await registerFreshUser(page);

  await page.getByTestId("file-input").setInputFiles({
    name: "notes.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("hello, this is plain text pretending to be a PDF"),
  });

  await expect(page.getByRole("alert").filter({ hasText: "الملف لازم يكون بصيغة PDF." })).toBeVisible();
  await expect(page.getByText("لا توجد وثائق بعد")).toBeVisible();
});
