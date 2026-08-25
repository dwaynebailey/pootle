// Phase 0, stream D: curated smoke suite against a running Pootle
// instance (docker-compose.e2e.yml). Every journey here was validated by
// hand against the running stack before being written down - see
// PORTING.md for what's deliberately out of scope and why.
//
// Known, documented limits (not bugs in this suite):
//  - The nav chrome (login/logout state, username display) is rendered
//    entirely client-side; server HTML is identical for anon/authed
//    users except the CSRF token. So this suite authenticates via a
//    direct POST to the real login endpoint (the same one the JS login
//    modal itself calls) rather than clicking through a UI that doesn't
//    exist without JS, and verifies auth by requesting a permission-gated
//    page instead of looking for a "Sign out" link.
//  - django-allauth blocks login behind email verification; the e2e seed
//    (docker/e2e/entrypoint.sh) marks the admin's email verified
//    directly rather than running the confirmation-email flow.
//  - File upload's real endpoint expects file metadata the JS uploader
//    attaches that a plain form POST doesn't reproduce ("missing
//    X-Pootle-Path header") - out of scope until Phase 4 makes the real
//    uploader JS available to test through.
//  - The translate editor and the checks/search *results* views are
//    hash-routed and JS-mounted (#filter=...) - also out of scope until
//    Phase 4. This suite covers what's real without it: browsing,
//    permissions, admin pages, downloads, and the terminology manager.

const { test, expect } = require('@playwright/test');

const ADMIN_USER = 'admin';
const ADMIN_PASS = 'e2e-admin-pw';

async function getCsrfToken(request, url) {
  const res = await request.get(url);
  const body = await res.text();
  const match = body.match(/csrfmiddlewaretoken' value='([^']+)'/);
  if (!match) {
    throw new Error(`No CSRF token found on ${url}`);
  }
  return match[1];
}

/** Log in via the real login endpoint (see the file header for why). */
async function login(requestOrPage, username, password) {
  const csrf = await getCsrfToken(requestOrPage.request ?? requestOrPage, '/accounts/login/');
  const req = requestOrPage.request ?? requestOrPage;
  return req.post('/accounts/login/', {
    form: { login: username, password, csrfmiddlewaretoken: csrf },
    headers: { Referer: '/accounts/login/' },
    maxRedirects: 0,
  });
}

test.describe('Anonymous access', () => {
  test('homepage loads', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Pootle Translation Server/);
  });

  test('project listing shows real, seeded content', async ({ page }) => {
    await page.goto('/projects/terminology/');
    await expect(page).toHaveTitle(/Terminology/);
    const languageLinks = page.locator('a[href$="/terminology/"]');
    expect(await languageLinks.count()).toBeGreaterThan(10);
  });

  test('server admin is blocked for anonymous users', async ({ request }) => {
    const res = await request.get('/admin/languages/');
    expect(res.status()).toBe(403);
  });
});

test.describe('Authentication', () => {
  test('valid credentials authenticate', async ({ request }) => {
    const res = await login(request, ADMIN_USER, ADMIN_PASS);
    expect([301, 302, 303]).toContain(res.status());
    expect(res.headers()['location']).not.toContain('confirm-email');

    const adminRes = await request.get('/admin/languages/');
    expect(adminRes.status()).toBe(200);
  });

  test('invalid credentials do not authenticate', async ({ request }) => {
    const res = await login(request, ADMIN_USER, 'totally-wrong-password');
    expect(res.status()).toBe(200); // re-renders the login page, no redirect

    const adminRes = await request.get('/admin/languages/');
    expect(adminRes.status()).toBe(403);
  });

  test('logout clears the session', async ({ page }) => {
    await login(page, ADMIN_USER, ADMIN_PASS);
    expect((await page.request.get('/admin/languages/')).status()).toBe(200);

    await page.request.get('/accounts/logout/');

    expect((await page.request.get('/admin/languages/')).status()).toBe(403);
  });
});

test.describe('Authenticated journeys', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN_USER, ADMIN_PASS);
  });

  test('admin can reach the server-wide language admin', async ({ page }) => {
    await page.goto('/admin/languages/');
    expect(page.url()).toContain('/admin/languages/');
  });

  test('translation project page renders real, interactive-looking forms', async ({ page }) => {
    await page.goto('/af/terminology/');
    await expect(page).toHaveTitle(/Terminology.*Afrikaans/);
    await expect(page.locator('#id_search')).toBeAttached();
    await expect(page.locator('#js-file-upload-input')).toBeAttached();
  });

  test('terminology manager page renders', async ({ page }) => {
    await page.goto('/af/terminology/terminology/manage/');
    await expect(page).toHaveTitle(/Manage Terminology/);
  });

  test('PO export downloads a real file', async ({ page }) => {
    const res = await page.request.get('/export/?path=/af/terminology/');
    expect(res.status()).toBe(200);
    expect(res.headers()['content-disposition']).toContain('attachment');
    const body = await res.body();
    expect(body.length).toBeGreaterThan(1000);
  });
});
