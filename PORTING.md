# Porting plan: repo & branch strategy

> **Critical rule: no code is ever pushed to `upstream` (`translate/pootle`).**
> This fork is a one-way street — fixes may be pulled *from* upstream (see
> below), nothing is ever pushed *to* it. Locally, `upstream`'s push URL is
> set to a dummy value (`git remote set-url --push upstream
> DISABLED_DO_NOT_PUSH_TO_UPSTREAM`) so an accidental `git push upstream`
> fails immediately instead of reaching the real repo. Anyone re-cloning
> this fork should set that up again before doing any work.

This fork (`dwaynebailey/pootle`) is a personal effort to modernize Pootle
(Python 3, current Django, current dependencies — see the full audit for
detail). These are the Phase 0 / stream J decisions this file exists to
record, so they don't live only in chat history.

## Repo & remotes

- `origin` — `dwaynebailey/pootle`, this fork. `main` is the integration
  branch for the port and is the default branch.
- `upstream` — `translate/pootle`, the original project. Not tracking it as
  a merge target; there is no near-term plan to merge this work back.
- `master` on both remotes is kept as a plain mirror of upstream's `master`
  (fast-forward only) — a reference point, not a working branch.

## Working-branch strategy

- Port work happens on long-lived branches per phase (e.g.
  `python3-port`, `django-ladder`), rebased periodically against this
  fork's `main` — not against upstream. Given the scope (cross-cutting
  framework changes across ~39k lines, single-maintainer effort),
  trunk-based feature flags aren't worth the overhead; a rebased long-lived
  branch per phase is the better fit.
- Each phase branch merges into `main` when its own exit criteria (see the
  audit's roadmap) are met.

## Taking fixes from upstream

- No freeze policy applies to upstream's `master` — it isn't this fork's
  responsibility. Instead: periodically (quarterly, by default) review
  `upstream/master` for genuine bugfixes and security patches and
  cherry-pick or merge them into `main`, so this fork doesn't drift on
  things unrelated to the port.
- Skip anything upstream that's purely stylistic or unrelated to
  correctness/security, to keep the diff against upstream legible.

## Recruitment / merging back

- Deferred. No public plan announcement, no upstream PR, while this stays
  a private, personal fork. Revisit once the port is stable enough to
  show.

## Phase 0 baselines (streams B & C)

`.github/workflows/old-stack-ci.yml` runs the pre-port test suite on every
push to `main`, against sqlite/postgres/mariadb, using
`docker/ci/Dockerfile`. It's a control channel, not the app's eventual CI —
it exists so every later porting phase has a trusted "old behavior" to
diff against.

**Pass-count baseline** (2026-08-23): 2286 passed / 123 failed / 94 error
(sqlite), 2285 / 2285 (postgres), 2295 (mariadb), out of ~2503 collected.
Non-passing results are >90% one already-understood, already-deferred
cause: `js/vendor.bundle.js` needs a real webpack build, out of scope
until the Phase 4 frontend rebuild. The workflow fails a job only if the
pass count drops below a floor (2200), not on pytest's own exit code — a
control channel permanently red on a known baseline can't signal an
actual regression.

**Coverage baseline** (2026-08-24, stream C): **88.8%** (`pootle` package,
17,859 statements / 2,002 missed — see `.coveragerc`), measured on the
sqlite leg only (coverage is a code-path property, not really
DB-backend-specific). The workflow fails if coverage drops below 85%.
Later phases (1-5) should not lower this without a deliberate reason.

**`filterwarnings = error` in `setup.cfg`** treats deprecation warnings in
in-house code as build breaks today, which is useful now but will need
retuning at each step of the Phase 2 Django ladder (1.11→2.2→3.2→4.2→5.2)
— each hop is expected to introduce new deprecation warnings on the way
to the next version, and the filter list will need new entries rather
than a blanket loosening.

**The real gap stream C surfaced:** every test in this repo (204 files)
is unit/integration level via Django's test client — there is no
browser-level or JS-integration test anywhere. That's exactly what a
Django-version-ladder-plus-React-rewrite can silently break without
either the Python test suite or a human noticing. Streams D (a curated
Playwright smoke suite over the actual user journeys) and E (golden-master
snapshots of API/page output for a frozen dataset) exist specifically to
close this gap before Phase 1 starts.

## Stream D: e2e smoke suite, and how much of the UI is JS-only

`docker-compose.e2e.yml` + `docker/e2e/` bring up a minimally-seeded,
real running instance (real Postgres, real Redis, real `initdb` demo
data — a "terminology" project across dozens of languages). `e2e/` is a
separate Playwright project (current Node/Playwright, unrelated to the
legacy `pootle/static/js/` toolchain) that drives it —
`.github/workflows/e2e-smoke.yml` runs it on every push to `main`.

Getting a real browser suite running surfaced something bigger than
expected: **far more of the UI is JS-only than just the translate
editor.** In order of discovery:

1. Every page using `{% assets 'js_*' %}` (i.e. almost every page)
   references literal pre-built webpack output
   (`pootle/apps/pootle_app/assets.py`) with no source list for
   webassets to assemble — `ASSETS_DEBUG` (stream B/C's fix for the CSS
   bundles) doesn't help here. `docker/e2e/stub-assets.sh` drops empty
   placeholder files at the expected paths purely so pages don't 500 on
   load; it produces zero working JS and is never committed
   (`*.bundle.js` is already gitignored). Goes away when Phase 4 lands
   real bundles.
2. **The login form doesn't exist in server HTML at all.** `/accounts/login/`
   renders the same shell page as everywhere else and relies on
   `PTL.auth.open(...)` (JS) to open a modal. With JS stubbed, there is
   no login UI to click.
3. **The whole nav chrome (logged-in state, username, logout link) is
   client-rendered too** — server HTML for `/` is byte-identical for
   anonymous and authenticated users except the CSRF token.
4. The upload form *is* real, server-rendered HTML
   (`#js-upload-form`, `action=""`) — but its real submission path
   expects file metadata (`X-Pootle-Path`) the JS uploader attaches
   that a plain form POST doesn't reproduce.
5. The checks and search *results* views are hash-routed
   (`/translate/#filter=...`) and entirely client-mounted.

None of this is new brokenness — it's how this version of the UI has
always worked, just invisible until something tries to test it without a
JS engine attached. The smoke suite works around (1)-(3) by
authenticating via a direct POST to the real login endpoint (the same
one the JS modal calls) rather than clicking a UI that doesn't render,
and verifying "authenticated" by requesting a permission-gated page
rather than looking for UI chrome that isn't server-rendered. (4) and
(5) are out of scope until Phase 4.

Also needed: `django-allauth` blocks login behind email verification
regardless of `is_superuser`; the seed script
(`docker/e2e/entrypoint.sh`) marks the seeded admin's email verified
directly (`EmailAddress.objects.get_or_create(..., verified=True)`)
rather than running the real confirmation-email flow.

**Covered by the suite (10 tests, all passing as of 2026-08-25):**
anonymous homepage/project-listing load, anonymous admin access is
blocked, login with valid/invalid credentials, logout clears the
session, authenticated server-admin access, a translation project page
renders its real forms, the terminology manager page renders, PO export
downloads a real file.

**Deliberately deferred to Phase 4:** the translate editor itself, the
login/signup modal as a UI interaction, file upload as a UI interaction,
and checks/search results pages — all genuinely need real JS to test
meaningfully, not just a passing HTTP status.

## Stream E: golden-master snapshots

`e2e/snapshot.js` captures a **normalized** fingerprint — record counts,
field-name schemas, and content-derived stable identifiers (language/
project codes, usernames), plus page title and a couple of structural
element counts — against the same deterministic e2e-seeded instance
stream D uses, and diffs it against the committed baseline
(`e2e/snapshots/baseline.json`). Wired into
`.github/workflows/e2e-smoke.yml` right after the Playwright suite, same
running stack, no extra infra.

Deliberately not raw bytes or exact JSON: the plan's own guidance was to
avoid that given the Phase 4 rewrite, and it turned out to matter for
JSON too, not just HTML — record `pk`s, timestamps, and exact markup are
all expected to shift across the port, so diffing them literally would
just be noise. What this *is* built to catch: a field disappearing from
an API response, a collection unexpectedly emptying out, or a page
starting to error or lose content it's expected to have.

One deviation from the original plan worth recording: rather than
building a second, separate seeding path from `pytest_pootle`'s
factories/`env.py` (streams B/C already exercise those, extensively, via
the pytest suite itself), this reuses stream D's `initdb`-seeded e2e
stack — it was already built, already validated, and is just as
deterministic (same script, same bundled content, same result every
run). Trade-off: the dataset is real demo content (a "terminology"
project) rather than data purpose-built to exercise suggestions/TM/
permissions edge cases the way `pytest_pootle/env.py` is — that
depth of coverage already exists in the pytest suite (streams B/C);
stream E's job is specifically to catch drift in what a browser/API
client actually sees, which the pytest suite can't.

Verified the check mechanism actually catches drift (not just always
passing): corrupted a value in the baseline, confirmed a nonzero exit
and a reported diff, restored it.

Snapshotted endpoints: `/xhr/admin/languages/`, `/xhr/admin/projects/`,
`/xhr/admin/users/` (JSON), and `/`, `/projects/terminology/`,
`/af/terminology/`, `/af/terminology/terminology/manage/` (HTML
title + structural counts).

## Stream G: dependency & security baseline

`tools/security-audit.py` queries [OSV.dev](https://osv.dev)'s API
directly by name+version for every package in `requirements/base.lock.txt`
and `pootle/static/js/package.json`. Not `pip-audit`/`npm audit`'s normal
path — both tried to actually build/install the pinned packages first to
get their metadata, and hit the same class of failure as the rest of
Phase 0 (`pip-audit` failed on `django-allauth==0.35.0`'s `setup.py`
importing `setuptools.convert_path`, which current setuptools removed).
Querying OSV directly by name+version sidesteps needing to build
anything.

**PyPI side** (`requirements/base.lock.txt`, 45 packages, run
2026-08-25) — 11 packages carry advisories against the exact pinned
version:

| Package | Advisories | Worth flagging |
|---|---|---|
| `Django==1.11.29` | 16 | SQL injection via `QuerySet` `_connector` kwarg (GHSA-frmv-pr5f-9mcr), another via column aliases (GHSA-6w2r-r2m5-xq5w), signed-cookie salt-namespace collisions, cache-disclosure issues |
| `bleach==2.1.3` | 10 | Multiple XSS/mutation-XSS bypasses, a ReDoS |
| `lxml==4.2.6` | 10 | XXE via default `iterparse()`/`ETCompatXMLParser()` config, XSS in the HTML cleaner |
| `urllib3==1.26.20` | 10 | — |
| `requests==2.27.1` | 8 | `.netrc` credential leak via crafted URLs |
| `django-allauth==0.35.0` | 6 | Open redirect, inactive-user access tokens accepted |
| `certifi==2021.10.8` | 6 | Distrusted root certs still shipped (GLOBALTRUST, TrustCor, e-Tugra) |
| `idna==2.10` | 4 | A DoS |
| `Babel==2.5.3` | 2 | Directory traversal |
| `Markdown==2.6.11` | 2 | — |
| `click==7.1.2` | 1 | — |

**npm side** (`pootle/static/js/package.json`, ranges resolved to their
minimum version — no committed lockfile, so these are approximate):
`lodash@4.2.1` (9 advisories), `underscore@1.6.0` (2),
`codemirror@5.7.0` (1), `select2@4.0.3` (1).

This re-orders priority within phases already on the roadmap rather than
adding new work: the Django-heavy PyPI list is exactly why the Phase 2
ladder is already the largest line item, and most of the rest
(`certifi`/`idna`/`urllib3`/`requests`/`bleach`/`lxml`/`Babel`/`Markdown`)
are transitive dependencies that get fixed for free the moment `base.txt`
itself moves off pins that predate Python 3 support — they don't need
individual attention. The npm findings land squarely in the already-
deferred Phase 4 frontend rebuild.

Raw OSV responses (verbose descriptions/references, ~600KB) aren't
committed — regenerate via `python3 tools/security-audit.py --json
<path>`.

## Stream H: config & secrets hygiene

Audited every committed config file (`docker/settings.conf`,
`docker/settings.postgres.conf`, `docker/settings.mariadb.conf`,
`docker/e2e/91-e2e.conf`) for real vs. placeholder secrets: every
`SECRET_KEY` is the literal string `'SECRETKEY'` (or, for the e2e-only
config, `'e2e-not-a-real-secret'`), every database password is
`'CHANGEME'` — clearly placeholders, not real credentials.
`.gitignore` already excludes where real local overrides would go
(`pootle/settings/*-local.conf`, `.env`).

Confirmed directly (2026-08-25): **no live Pootle instance runs on this
codebase**, so there's nothing that could have inherited these demo
defaults as production values. Closes this stream.

Intended pattern for later (formalized properly in the Docker & cloud
packaging work, not needed for Phase 0 itself): secrets injected via
environment variables at deploy time (e.g. `django-environ` reading
`SECRET_KEY`/`DATABASE_PASSWORD` from the environment), nothing baked
into an image or committed to a conf file. The current placeholder
pattern (`docker/settings*.conf`) is fine for local dev/CI, where the
values are genuinely throwaway per-container.

## Stream I: live-data safety

**Not applicable — explicitly marked skipped, not left ambiguous.**
Confirmed directly (2026-08-25): no production or staging Pootle
instance exists under this fork's — or anyone's — active care right
now. Nothing to back up before this port touches data.
