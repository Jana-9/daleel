import { expect, test, type Page } from "@playwright/test";

const PASSWORD = "s3cure-pass";

function uniqueEmail() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function register(page: Page, email: string) {
  await page.goto("/register");
  await page.getByLabel("الاسم").fill("جنى");
  await page.getByLabel("البريد الإلكتروني").fill(email);
  await page.getByLabel("كلمة المرور").fill(PASSWORD);
  await page.getByRole("button", { name: "إنشاء الحساب" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test("landing page has no horizontal scroll and links to sign-up", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
  await page.getByRole("link", { name: "ابدئي مجانًا" }).click();
  await expect(page).toHaveURL(/\/register$/);
});

test("register validates input before calling the server", async ({ page }) => {
  await page.goto("/register");
  await page.getByRole("button", { name: "إنشاء الحساب" }).click();
  await expect(page.getByText("الاسم لازم يكون حرفين على الأقل.")).toBeVisible();
  await expect(page.getByText("كلمة المرور لازم تكون 8 أحرف على الأقل.")).toBeVisible();
});

test("full session: register, logout, failed login, login", async ({ page }) => {
  const email = uniqueEmail();
  await register(page, email);
  await expect(page.getByRole("heading", { name: "أهلًا جنى" })).toBeVisible();

  // A logged-in user who opens /login is sent back to the dashboard.
  await page.goto("/login");
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.getByRole("button", { name: "خروج" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("البريد الإلكتروني").fill(email);
  await page.getByLabel("كلمة المرور").fill("wrong-password");
  await page.getByRole("button", { name: "تسجيل الدخول" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "البريد الإلكتروني أو كلمة المرور غير صحيحة." }),
  ).toBeVisible();

  await page.getByLabel("كلمة المرور").fill(PASSWORD);
  await page.getByRole("button", { name: "تسجيل الدخول" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("duplicate email shows a clear error", async ({ page, browser }) => {
  const email = uniqueEmail();
  await register(page, email);

  const other = await (await browser.newContext()).newPage();
  await other.goto("/register");
  await other.getByLabel("الاسم").fill("جنى");
  await other.getByLabel("البريد الإلكتروني").fill(email.toUpperCase());
  await other.getByLabel("كلمة المرور").fill(PASSWORD);
  await other.getByRole("button", { name: "إنشاء الحساب" }).click();
  await expect(
    other.getByRole("alert").filter({ hasText: "يوجد حساب مسجّل بهذا البريد الإلكتروني." }),
  ).toBeVisible();
});

test("dashboard redirects to login without a session", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login$/);
});
