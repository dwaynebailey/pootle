#!/usr/bin/env node
// Phase 0, stream E: golden-master snapshots against the deterministic
// e2e-seeded instance (docker-compose.e2e.yml - real Postgres, real
// initdb demo data, same script + same bundled content every run).
//
// Deliberately normalized, not raw bytes: record counts, field-name
// schemas, and content-derived stable identifiers (language/project
// codes, usernames), not literal JSON or HTML strings. Raw values (pks,
// timestamps, exact markup) are expected to shift across the port -
// see PORTING.md - so diffing them here would just be noise. What this
// *should* catch: a field disappearing, a collection emptying out, a
// page starting to 500 or losing content it's expected to have.
//
// Usage:
//   node snapshot.js --write   capture fresh, overwrite snapshots/baseline.json
//   node snapshot.js           capture fresh, diff against the committed baseline

const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.POOTLE_E2E_BASE_URL || 'http://localhost:8000';
const BASELINE_PATH = path.join(__dirname, 'snapshots', 'baseline.json');
const ADMIN_USER = 'admin';
const ADMIN_PASS = 'e2e-admin-pw';

let cookieJar = {};

function withCookies(headers = {}) {
  const cookie = Object.entries(cookieJar).map(([k, v]) => `${k}=${v}`).join('; ');
  return cookie ? { ...headers, Cookie: cookie } : headers;
}

function storeCookies(res) {
  const raw = res.headers.getSetCookie ? res.headers.getSetCookie() : [];
  for (const line of raw) {
    const [pair] = line.split(';');
    const [k, v] = pair.split('=');
    cookieJar[k.trim()] = v;
  }
}

async function get(urlPath) {
  const res = await fetch(`${BASE_URL}${urlPath}`, { headers: withCookies(), redirect: 'manual' });
  storeCookies(res);
  return res;
}

async function login() {
  const loginPage = await get('/accounts/login/');
  const body = await loginPage.text();
  const match = body.match(/csrfmiddlewaretoken' value='([^']+)'/);
  if (!match) throw new Error('No CSRF token found on /accounts/login/');

  const res = await fetch(`${BASE_URL}/accounts/login/`, {
    method: 'POST',
    redirect: 'manual',
    headers: withCookies({
      'Content-Type': 'application/x-www-form-urlencoded',
      Referer: `${BASE_URL}/accounts/login/`,
    }),
    body: new URLSearchParams({
      login: ADMIN_USER,
      password: ADMIN_PASS,
      csrfmiddlewaretoken: match[1],
    }),
  });
  storeCookies(res);
  if (![301, 302, 303].includes(res.status)) {
    throw new Error(`Login did not redirect (got ${res.status}) - check credentials/seed`);
  }
}

/** Normalize an /xhr/admin/* {models: [...]} response. */
async function snapshotAdminList(urlPath, idField) {
  const res = await get(urlPath);
  if (res.status !== 200) {
    return { status: res.status };
  }
  const data = await res.json();
  const models = data.models || [];
  return {
    status: 200,
    count: models.length,
    fields: models.length ? Object.keys(models[0]).sort() : [],
    ids: models.map((m) => m[idField]).sort(),
  };
}

/** Normalize an HTML page: status, title, and a few structural counts. */
async function snapshotPage(urlPath, selectors) {
  const res = await get(urlPath);
  if (res.status !== 200) {
    return { status: res.status };
  }
  const html = await res.text();
  const title = (html.match(/<title>([^<]*)<\/title>/) || [, null])[1];
  const counts = {};
  for (const [name, re] of Object.entries(selectors || {})) {
    counts[name] = (html.match(new RegExp(re, 'g')) || []).length;
  }
  return { status: 200, title, counts };
}

async function capture() {
  await login();

  return {
    admin_languages: await snapshotAdminList('/xhr/admin/languages/', 'code'),
    admin_projects: await snapshotAdminList('/xhr/admin/projects/', 'code'),
    admin_users: await snapshotAdminList('/xhr/admin/users/', 'username'),

    homepage: await snapshotPage('/'),
    project_listing: await snapshotPage('/projects/terminology/', {
      language_links: 'href="/[a-z_]+/terminology/"',
    }),
    translation_project: await snapshotPage('/af/terminology/', {
      search_input: 'id="id_search"',
      upload_input: 'id="js-file-upload-input"',
    }),
    terminology_manager: await snapshotPage('/af/terminology/terminology/manage/'),
  };
}

function diff(baseline, current, prefix = '') {
  const diffs = [];
  const keys = new Set([...Object.keys(baseline), ...Object.keys(current)]);
  for (const key of keys) {
    const path = prefix ? `${prefix}.${key}` : key;
    const b = baseline[key];
    const c = current[key];
    if (typeof b === 'object' && b !== null && typeof c === 'object' && c !== null && !Array.isArray(b)) {
      diffs.push(...diff(b, c, path));
    } else if (JSON.stringify(b) !== JSON.stringify(c)) {
      diffs.push(`${path}: ${JSON.stringify(b)} -> ${JSON.stringify(c)}`);
    }
  }
  return diffs;
}

async function main() {
  const snapshot = await capture();

  if (process.argv.includes('--write')) {
    fs.mkdirSync(path.dirname(BASELINE_PATH), { recursive: true });
    fs.writeFileSync(BASELINE_PATH, JSON.stringify(snapshot, null, 2) + '\n');
    console.log(`Wrote baseline: ${BASELINE_PATH}`);
    return;
  }

  if (!fs.existsSync(BASELINE_PATH)) {
    console.error(`No baseline at ${BASELINE_PATH} - run with --write first.`);
    process.exit(1);
  }
  const baseline = JSON.parse(fs.readFileSync(BASELINE_PATH, 'utf8'));
  const diffs = diff(baseline, snapshot);

  if (diffs.length === 0) {
    console.log('No drift from the golden-master baseline.');
    return;
  }

  console.error(`${diffs.length} drift(s) from the golden-master baseline:`);
  for (const d of diffs) console.error(`  ${d}`);
  process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
