#!/usr/bin/env node
// Phase 0, stream F: performance baseline against stream D's e2e stack.
// Response-time percentiles for representative pages, on the real
// initdb-seeded dataset (a "terminology" project across ~57 languages,
// tens of thousands of units combined - already at the scale the plan
// called for, no separate dataset needed).
//
// Not a literal RQ-queue throughput number: this version's RQ usage
// turned out to be far lighter than assumed (grep found only 3 files
// referencing django_rq directly, not a heavy background-job pipeline)
// - documented as a real finding rather than forcing a queue-throughput
// measurement that doesn't reflect how this version actually works.
// `refresh_scores` (recalculates scores for every unit in the dataset)
// is the closest real analog to "stats recalculation" and is measured
// as a wall-clock throughput number instead.

const BASE_URL = process.env.POOTLE_E2E_BASE_URL || 'http://localhost:8000';
const ADMIN_USER = 'admin';
const ADMIN_PASS = 'e2e-admin-pw';
const N = 20;

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
  const res = await fetch(`${BASE_URL}${urlPath}`, { headers: withCookies() });
  storeCookies(res);
  return res;
}
async function login() {
  const loginPage = await get('/accounts/login/');
  const body = await loginPage.text();
  const csrf = body.match(/csrfmiddlewaretoken' value='([^']+)'/)[1];
  const res = await fetch(`${BASE_URL}/accounts/login/`, {
    method: 'POST',
    redirect: 'manual',
    headers: withCookies({
      'Content-Type': 'application/x-www-form-urlencoded',
      Referer: `${BASE_URL}/accounts/login/`,
    }),
    body: new URLSearchParams({ login: ADMIN_USER, password: ADMIN_PASS, csrfmiddlewaretoken: csrf }),
  });
  storeCookies(res);
}

function percentile(sorted, p) {
  const idx = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

async function timePage(urlPath, n) {
  const timings = [];
  for (let i = 0; i < n; i++) {
    const start = performance.now();
    const res = await get(urlPath);
    await res.text();
    timings.push(performance.now() - start);
    if (res.status !== 200) {
      console.error(`  ! ${urlPath} returned ${res.status} on request ${i + 1}`);
    }
  }
  timings.sort((a, b) => a - b);
  return {
    n,
    p50_ms: Math.round(percentile(timings, 50)),
    p95_ms: Math.round(percentile(timings, 95)),
    min_ms: Math.round(timings[0]),
    max_ms: Math.round(timings[timings.length - 1]),
  };
}

async function main() {
  await login();

  const pages = [
    '/',
    '/projects/terminology/',
    '/af/terminology/',
    '/af/terminology/translate/',
    '/af/terminology/terminology/manage/',
    '/admin/languages/',
  ];

  console.log(`Response times over ${N} requests each (ms):\n`);
  const results = {};
  for (const page of pages) {
    const r = await timePage(page, N);
    results[page] = r;
    console.log(`  ${page.padEnd(40)} p50=${r.p50_ms}  p95=${r.p95_ms}  min=${r.min_ms}  max=${r.max_ms}`);
  }

  console.log('\nBackground stats recalculation throughput (refresh_scores, whole seeded dataset):');
  console.log('  run separately via: docker compose -f ../docker-compose.e2e.yml exec web python2 manage.py refresh_scores');
  console.log('  (not run from this script - it mutates real data and takes several minutes on the full dataset)');

  console.log('\n' + JSON.stringify(results, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
