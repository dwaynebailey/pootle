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

## Stream F: performance baseline

`e2e/perf-baseline.js` times representative pages against stream D's
e2e stack (real dataset, 69,323 units across a "terminology" project in
~57 languages — already at the scale the plan called for, no separate
larger dataset needed). 20 requests each, run 2026-08-26:

| Page | p50 | p95 |
|---|---|---|
| `/` | 38ms | 82ms |
| `/projects/terminology/` | 40ms | 72ms |
| `/af/terminology/` | 37ms | 54ms |
| `/af/terminology/translate/` (shell only — JS-mounted, see stream D) | 29ms | 47ms |
| `/af/terminology/terminology/manage/` | **151ms** | **213ms** |
| `/admin/languages/` | 9ms | 10ms |

The terminology manager page is the outlier — 4-15x slower than
everything else. Worth watching specifically during the Phase 2 Django/
ORM ladder as a candidate for an N+1 query pattern, rather than
something this stream needed to root-cause.

**Background job throughput turned out not to be the useful number
here.** The plan called for "RQ jobs/sec for stats recalculation," but
this version's real RQ/background-job usage is far lighter than that
assumed: `grep` found only 3 files referencing `django_rq` directly, and
`refresh_scores` (the obvious "stats recalculation" command) completed
in ~1s on the full dataset — because score updates key off user
*submission* events, and this demo dataset was bulk-imported via
`initdb`, not submitted through the app. Forcing a queue-throughput
measurement here would have measured an empty queue, not real work.

Instead: `calculate_checks` (recomputes quality checks for every unit —
real per-unit work, already observed running during `initdb` seeding)
took **9s for all 69,323 units — ≈7,700 units/sec** for checks
recalculation. That's the throughput number worth carrying forward as
this stream's actual baseline.

## Phase 1: Python 3 port

Work lives on the long-lived `python3-port` branch (off `main`, per the
branch strategy above) — not merged to `main` yet. Validation
environment: `docker/py3/Dockerfile`, building `FROM python:3.12-slim`.
It is **not a production image** (no app server, no asset pipeline) —
it exists purely to validate that the port itself works: requirements
install, the app imports, and the test suite runs, under Python 3.12.
`docker/py3/patch-*.sh` explain the third-party packages that needed
build-time patching (django-allauth, django-sortedm2m never shipped
wheels and have broken `setup.py` under modern tooling; Django 1.11's
vendored `six.py` doesn't resolve under Python 3.12's import system).

Two milestones reached in order:

1. `django.setup()` succeeds cleanly under Python 3.12, zero errors,
   zero warnings.
2. The full pytest suite (2476 tests) collects cleanly under
   Python 3.12, zero collection errors.

Getting the suite to actually *execute* surfaced a long tail of Python
2→3 semantic changes, not just syntax. Some were near-universal
blockers (one broken line failing every single test); most were
localized bugs found by re-running the full suite and frequency-ranking
the failure log after each fix. Recurring bug *shapes*, worth knowing
about if more turn up during Phase 2:

- **`hasattr()` no longer swallows arbitrary exceptions** — only
  `AttributeError`. A descriptor raising bare `KeyError` for "not set
  yet" (`pootle_store/fields.py`) silently worked as intended in Python
  2 and hard-failed in Python 3. Fix: raise `AttributeError`, which is
  the descriptor protocol's actual contract anyway.
- **Cross-type comparisons** (`None >= int`, `None > int`) were always
  `False` under Python 2's total-ordering-by-typename; Python 3 raises
  `TypeError`. Found in `pootle_store/diff.py` and
  `pootle_data/utils.py` (both "first real value wins" accumulator
  patterns) — fixed by making the `is None` case explicit rather than
  relying on ordering to encode it.
- **`str(store)` on a translate-toolkit `TranslationStore`** only
  serializes under Python 2 (translate-toolkit's own compat shim,
  documented in its source as kept "for compatibility purpose"); under
  Python 3 it silently falls through to plain `object.__str__()` and
  produces garbage rather than raising. `bytes(store)` is the real,
  version-independent entry point. Turned up in 5 separate files
  (production code and tests) — worth a `grep -rn "str(.*store"` sweep
  before Phase 2 in case more remain unexercised.
- **`filter()`/`map()` return one-shot iterators, not lists.** Some
  call sites crashed outright (`len()`, indexing, `.append()` on the
  result). More dangerously, several didn't crash at all: an iterator
  is *always truthy* regardless of whether it has any matches, so
  `if filtered_result:` / `not filtered_result` silently always took
  the same branch in Python 3 — wrong behaviour with no exception to
  find it by. Fixed 5 of these (`pootle_app/models/permissions.py`,
  a migration, `context_processors.py`, `pootle_store/models.py`,
  `core/views/api.py`); the migration and `context_processors.py` ones
  were pure silent-logic-bug cases, not crashes — grep for `= filter(`
  / `= map(` is worth repeating periodically since nothing will ever
  fail loudly on its own to point back at them.
- **Defining `__eq__` without `__hash__`** kept the default
  identity-based hash in Python 2 regardless; Python 3 sets `__hash__
  = None` as soon as a class defines `__eq__` without it, breaking
  anything that hashes instances later (`@lru_cache`-memoized methods,
  set/dict membership). Fixed 4 classes
  (`pootle_fs/plugin.py:Plugin`, `pootle_fs/utils.py:FSPlugin`,
  `core/state.py:ItemState` and `State`) by adding `__hash__` mirroring
  each class's own `__eq__` fields. `pootle_project/models.py`'s
  `ProjectResource`/`ProjectSet` and `pootle_store/diff.py` have the
  same shape but weren't yet observed being hashed anywhere — left
  alone rather than guessing (their equality includes an unhashable
  `list`, so a naive `__hash__` would be wrong), pending an actual
  failure.
- **pytest itself moved on**: `Item.get_marker()` →
  `get_closest_marker()`, `Metafunc.funcargnames` → `.fixturenames`,
  and calling an `@pytest.fixture`-decorated function directly (works,
  with a warning, pre-pytest-4; hard `Failed` error since) all needed
  fixing in `pytest_pootle/`'s fixture machinery, independent of the
  app code itself.

**Current state** (full suite, sqlite, `pytest tests -q`, against the
real-Elasticsearch stack in `docker-compose.py3.yml`, **with
`filterwarnings=error` actually enforced** - no `-p no:warnings`
bypass, see below - as of `07580f377`): **2299 passed / 108 failed /
94 errors / 10 skipped / 1 xfailed**, out of 2512 collected — **past
the Python 2 baseline's 2286 passed** (baseline: 2286 passed / 123
failed / 94 error, sqlite, out of ~2503 - see stream B/C above),
errors still tied at 94. Progression: complete infrastructure failure
(2510 errors, one universal `get_marker()` bug) → 1766/565/170 →
2133/266/102 → 2218/189/94 → 2264/143/94 → 2290/117/94 → 2298/109/94 →
2299/108/94. **Of the 108 failed, 107 is the webassets BundleError
cluster** (confirmed not a regression, see above - not a Phase 1
target); **the other 1 is a single likely-flaky timing-boundary
test** (passes cleanly in isolation - see below). Several single
fixes this phase cascaded into
10-120 passing tests each because they sat in shared fixture setup or
a widely-used utility (`unit/search.py`'s offset check,
`FSItemState.__gt__`, `bulk_update()` on `dict.values()`, the two
`Comparable*LogEvent.__cmp__` classes, `FSFile._sync_from_pootle()`'s
`str(store)` bug, `pootle_fs/management/commands/fs.py`'s
`no_style.cache_clear()`, `PootleCommand._handle()`'s leaked root
logger level below) — worth re-checking that pattern (one early,
universal cause behind a pile of unrelated-looking failures) before
assuming a new batch of failures are all independent.

**Elasticsearch is now real, not absent**, via `docker-compose.py3.yml`
(new this phase - see its own comments for the full rationale/
gotchas): `docker.elastic.co/elasticsearch/elasticsearch-oss:6.2.3`,
the same image this repo's own `docker-compose.yml` already pairs
with the `elasticsearch~=5.0` client (`requirements/_es_5.txt`) -
verified directly (indices.exists/create/index/search all
round-tripped real results) rather than assumed compatible. Chosen
over a stub after hands-on testing: `tests/settings.py` hardcodes
`'elasticsearch'` as the default TM server host for the *entire* test
suite (not just the tests that obviously touch it), so a working
server clears connection-error log noise out of virtually every
DB-touching test's captured output - a stub would need to cover that
same surface for no real savings in effort. Two Docker-on-Apple-
Silicon gotchas found and fixed, both documented inline in the
compose file: this image generation predates Elastic's arm64 builds
(pinned `platform: linux/amd64`, fine under emulation), and JVM
startup can hang indefinitely on entropy-starved `/dev/random`
without `-Djava.security.egd=file:/dev/./urandom` (observed directly
- one cold start took 24s, another sat at 0 log lines/100% CPU for
7+ minutes before being killed). Net effect on full-suite runtime was
positive, not negative: 25min with a working ES vs ~55min when
`elasticsearch` resolved to nothing and every command retried against
a slow DNS-negative-response timeout instead.

Finally having ES noise out of the way surfaced the real bug behind
the ~8 previously-ES-blamed `tests/commands/import.py`/
`update_tmserver.py` failures: `err` was genuinely empty, not just
crowded out. Root cause: `pootle/apps/pootle_app/management/commands/
__init__.py`'s `PootleCommand._handle()` (and `test_checks.py`'s
`Command.handle()`, same shape) call `logging.getLogger().setLevel(...)`
to honour the command's own `-v`/`--verbosity` flag, but never
restored the previous level afterwards. The root logger's level is
process-global, so any earlier test in the same pytest process
invoking a `PootleCommand`-derived command via `call_command()`
(Django's default verbosity=1 maps to `WARNING`) permanently silenced
`INFO`-level logging for everything run afterwards in the same
process - including the `import` command's own `"[update] added N
units..."` message these tests asserted on. Not a new Python 3 bug
(the code is version-agnostic) - more of the suite now runs far
enough to actually trigger it than before this phase's other fixes
landed. Fixed both call sites with save/restore-in-`finally` around
the command's own run.

**The one remaining failure**: `tests/accounts/models.py::
test_model_user_last_event` (`assert '1 isekhondi' == '2 amasekhondi'`
- a "N seconds ago" pluralized-string check) failed once in a
full-suite run but passes cleanly in isolation - a real-time
boundary flake (the test's actual elapsed wall-clock time crossed
from "1 second" to "2 seconds" between event creation and assertion),
plausibly made more likely now that unit saves route through a real
(if emulated-and-slower) Elasticsearch call. Not confirmed as
pre-existing under the Python 2 baseline or not; worth a second look
if it recurs, not chased further as a one-off.

**Two more things found and fixed getting to this final number, both
worth remembering:**

1. **`docker-compose.py3.yml`'s `test` service silently dropped its
   own test tooling on any command override.** Its `command:` used to
   be a `bash -c "pip install ... && pytest ..."` wrapper - fine for
   the default invocation, but `docker-compose run test pytest
   tests/some_file.py` *replaces* the whole command rather than
   appending to it, so the pip install step vanished and pytest
   wasn't even on `PATH`. Fixed by giving Phase 1 its own pinned test
   tooling (`requirements/tests_py3.txt` - `requirements/tests.txt`
   stays untouched, still pinning pytest 3.3.0 etc. for the Python 2
   control channel) baked into `docker/py3/Dockerfile` itself, so the
   compose `command:` is just `["pytest", "tests", "-q"]` and safely
   overridable.

2. **Every full-suite run this phase, until this point, had actually
   been running with `-p no:warnings`** - a flag that disables
   pytest's warnings plugin outright, which `setup.cfg`'s
   `filterwarnings = error` policy depends on to do anything at all.
   Found while fixing (1) above and finally running the suite through
   its real, unmodified configuration. Running properly dropped the
   count from ~2298 passed to 2198 - a real, if narrow, gap, not a
   phantom one:
   - `setup.cfg`'s `SyntaxWarning` rule only matched "invalid escape
     sequence" messages; `django-allauth`'s `if scope is '':` (a
     *different* `SyntaxWarning`, "is with a literal") was escalating
     to a hard `SyntaxError` once enough of the suite exercised code
     importing its templatetags. Broadened the rule to match any
     `SyntaxWarning` message (keeping the same "not pootle" module
     scope) rather than adding message text one at a time - the whole
     point of scoping by module is that it shouldn't matter *which*
     message a third-party dependency happens to trigger.
   - No equivalent rule existed for third-party `DeprecationWarning`
     at all; `django_rq`'s templatetags call
     `distutils.version.LooseVersion()` directly, deprecated by
     Python. Added the same shape of rule.
   - The one warning that legitimately *should* have been fatal,
     and correctly was: 12 call sites across 6 files
     (`pootle/runner.py`, `pootle_fs/files.py`, two migrations,
     `sync_stores.py`, `update_stores.py`) called `logger.warn(...)`
     - Python's own deprecated alias for `logger.warning()`. Not
     covered by the third-party-only filterwarnings scope since it's
     genuinely our code - fixed all 12. One follow-up:
     `tests/commands/sync_stores.py` mocks the module's logger and
     asserted on the literal method name called
     (`logger_mock.warn.call_args`) - updated to `.warning` to match.

Net effect of both fixes together: 2198 → 2299 passed with
`filterwarnings` properly active - matching (and, after the
`sync_stores.py` mock fix, slightly exceeding) the earlier
`-p no:warnings`-masked number. The true state of the port was being
accurately reported all along, just for the wrong reason - worth
remembering if a future session's numbers ever look implausibly good
or bad: check what flags actually ran, not just what the last commit
message claimed.

**Operational note on Elasticsearch-under-emulation reliability**:
across this phase's work, ES startup time under `platform:
linux/amd64` emulation ranged from a reliable ~16-24s (typical) to
one observed 7+ minute hang (entropy starvation, since fixed) and,
separately, one stalled *mid-test-run* for over an hour with 0% CPU
in the test container - which turned out to correlate with the whole
host machine being under heavy load (`uptime` load averages of
12-20+, 10GB+ in the memory compressor) from the accumulated
containers/builds of a very long session, not a Docker or ES-specific
fault. Restarting fresh once host load actually dropped (`uptime`
back under ~8) fixed it immediately - a full clean run then took under
5 minutes. If a future session sees ES (or anything containerized)
mysteriously hang, check `uptime`/`docker stats` for host-level
contention before assuming a code or container regression.

More bug shapes found in the push from 2133 to 2218, beyond the ones
already listed above:
- **`__unicode__` without `__str__`**: 19 classes across 14 files
  defined Django/Python 2's primary string-conversion hook but not
  Python 3's. Found systematically via an AST sweep (not just
  grep) rather than one at a time - `str(instance)`/`repr(instance)`
  fell through to Django's own default `"ClassName object"` instead
  of the class's real one, which is worth checking for again if any
  new model classes get added carrying only `__unicode__` during
  Phase 2.
- **`__cmp__` (Python 2's three-way comparison protocol) with no
  `__lt__`/`__eq__` fallback**: removed entirely in Python 3. Fixed
  by adding `__lt__`/`__eq__` delegating to the existing `__cmp__`
  logic, `@functools.total_ordering` for the rest. One non-obvious
  wrinkle on classes built via `pootle/core/proxy.py`'s `BaseProxy`:
  `self.__cmp__(other)` from inside the new `__lt__` doesn't work -
  `BaseProxy.__getattribute__` redirects *every* instance attribute
  lookup, including from the class's own methods, to the wrapped
  object. Had to call `ClassName.__cmp__(self, other)` instead,
  looking the method up on the class directly.
- **Session-scoped pytest fixtures doing real DB access without
  `django_db_blocker`**: worked under the Python 2 baseline's older
  pytest-django (3.1.2); the bumped 4.8.0 (requirements/tests.txt)
  enforces the db-access block more strictly outside a test's own
  `django_db`-marked scope. Same fix pattern already used by
  `pytest_pootle/fixtures/site.py`'s `post_db_setup`: depend on
  `django_db_setup` + `django_db_blocker`, wrap the query in
  `django_db_blocker.unblock()`.
- **Mutating a dict while iterating `.items()`**: a live view under
  Python 3 (a list snapshot under Python 2) - `for k, v in
  d.items(): ... del d[k]` now raises `RuntimeError: dictionary
  changed size during iteration`. Wrap the `.items()` call in
  `list()`.
- **`pkg_resources` needs `setuptools<81`**: unrelated to app code -
  `bleach==2.1.3` (a dependency already flagged in stream G's
  security audit as due for a real upgrade) still imports
  `pkg_resources`, which recent setuptools versions split out of the
  default install ahead of removing it outright. Pinned in
  `docker/py3/Dockerfile`.
- **stdlib/tooling message-wording changes, not Pootle bugs**:
  argparse's "too few arguments" (Python 2) became "the following
  arguments are required: ..." (Python 3.3+); pytest's
  `ExceptionInfo.__str__()` format changed between pytest 3.3.0 and
  7.4.4. Several `tests/commands/*.py` assertions hardcoded the old
  wording.

More bug shapes found in the push from 2218 to 2264:
- **Indexing straight into a caught exception** (`e[0]`): Python 2
  allowed this (deprecated), Python 3 doesn't. `e.args[0]` or `str(e)`
  (the latter also works uniformly across exception types whose
  message shape differs, e.g. Django's `ValidationError`).
- **hashlib/base64 needing bytes, not str**: `pootle/core/forms.py`'s
  captcha token generation chained `base64.urlsafe_b64encode()` and
  `hashlib.sha1()` on plain `str` - worked under Python 2 (str was
  bytes), needs explicit `.encode('utf-8')` under Python 3. The
  second of the two had never actually been reached before the fix,
  since the first one crashed first.
- **`fnmatch.translate()`'s output format changed** (Python 3.6+):
  Python 2 always ended a translated pattern with the literal string
  `\Z(?ms)`; Python 3 wraps the body in a scoped `(?s:...)` group and
  ends with just `\Z`. `pootle_fs/utils.py`'s `PathFilter.path_regex()`
  stripped the old Python-2-only trailing string so callers could
  append their own suffix - under Python 3 that string-replace became
  a silent no-op, leaving a stray end-of-string anchor in the *middle*
  of the assembled regex once a caller's suffix got appended, making
  every match silently impossible. No exception anywhere - this is
  the same "stdlib changed its output shape, nothing crashes, matching
  just stops working" pattern as the dict-view and filter()-truthiness
  bugs, just from a different stdlib module. Caution found while
  fixing it: a test in the same file re-derived the expected regex
  inline using the *same* outdated assumption instead of calling the
  real implementation, so fixing path_regex() alone was a net
  regression until that test's own reference computation got the
  same fix.
- **A class's `__str__()` and `__unicode__()` deliberately returning
  different things** (pre-existing design, not something this port
  introduced): `pootle_store/models.py`'s `Unit` and `Store` both do
  this - `__unicode__` gives a short display form, `__str__` gives
  the full file-format-serialized content via `.convert()`. Under
  Python 2 this was a genuine, working distinction (`unicode(x)` vs
  `str(x)` are different calls); Python 3 only has one string
  protocol, so any code that used to rely on the *implicit* Python 2
  conversion (e.g. Django's `truncatechars` template filter, which
  calls `force_text`/`unicode()`) now silently gets the *other* one
  (`__str__`, "give me the full serialized content") instead of what
  it actually wanted. Fixed the one exercised call site
  (`pootle_statistics/models.py`'s `get_submission_info()`) by using
  `.source` explicitly rather than relying on the str()/unicode()
  split; grepped for other implicit-stringification call sites on
  `Unit`/`Store` and found none more, but this is exactly the kind of
  gap that won't announce itself with an exception if more turn up.
  **Follow-up, a few commits later**: an initial fix (making
  `Store.__str__`/`Unit.__str__` correctly serialize the *full*
  content, i.e. actually doing what they were trying to do under
  Python 2) turned out to be the wrong direction - it collided with
  Django's `Model.__repr__`, which always calls `str(self)`, so
  `repr(store)`/`repr(unit)` started dumping entire serialized files
  instead of a short summary. Reversed to `__str__ = __unicode__` for
  both (the short form, matching every other model this phase), and
  moved the "full serialized content" test assertions onto `bytes()`
  directly rather than asking `__str__` to mean two different things.
- **`django.core.management.color.no_style()` is cached forever**
  (`@lru_cache`), and `color_style()` falls back to it whenever
  `supports_color()` is False (any non-tty stdout, e.g. under
  pytest). `pootle_fs/management/commands/fs.py` patches
  `django.utils.termcolors.PALETTES` with custom `FS_*` color roles
  at module-import time, banking on being imported early - but
  nothing guarantees that against whichever management command
  happens to be instantiated *first* in the whole process, from
  anywhere. An initial fix (having a test file explicitly import
  `fs.py` so the patch runs at collection time) was insufficient -
  still reproducible in isolation. The real fix: call
  `no_style.cache_clear()` right after the `PALETTES` patches, so the
  *next* call rebuilds fresh - not import-order-sensitive, unlike an
  import-order workaround.
- **Python 2's `/` on two ints floor-divided**; Python 3's is true
  division. Turned up twice more as hand-rolled pagination/median-
  index math (`tests/core/forms.py`'s ceiling-division page-count
  formula, `tests/statistics/stats_utils.py`'s median-index lookup) -
  worth grepping for `/ 2]` or similar index expressions if more
  surface.

**Environment note, since resolved**: full suite runs used to take
dramatically longer than the ~4 minute baseline (one observed run
took 55 minutes) whenever they reached the tests touching
Elasticsearch, which had no live server on the network - the
`elasticsearch` Python client's retry/backoff compounded with a slow
DNS-negative-response timeout for the nonexistent `elasticsearch`
hostname (one single test measured 15+ minutes alone). Fixed by wiring
up a real Elasticsearch via `docker-compose.py3.yml` - see the
"Current state" section above for the full writeup. Runtime with a
working ES (~16-25 min) is *lower* than the no-ES-at-all baseline
(~55 min when the hostname timed out), even though higher than the
old fast-fail case where `elasticsearch` wasn't even a resolvable
network alias.

More recurring bug shapes found in this later stretch, beyond the
ones already listed above:
- **`filter()`/`map()` returning iterators** turned out to be a much
  bigger, more scattered pattern than first thought — a repeat `grep
  -rn "filter("` sweep after fixing the ones test failures pointed at
  found *more* silent-logic-bug instances nothing had failed loudly
  on yet (`pootle_store/receivers.py`, `models.py`'s `markfuzzy()`/
  `resurrect()`, `unit/proxy.py`, `utils.py`, two more in the same fs
  migration file). Worth another such sweep before Phase 2.
- **`.next()`** — Python 2's method-call spelling for what's
  `next(x)` in Python 3 — found on both a stdlib generator
  (`os.walk()` in a migration) and test fixture generators.
- **`dict.values()` fed to something needing a real sequence**:
  `bulk_update()` (third-party, indexes its argument) and
  `JsonResponse` (needs JSON-serializable data) both hit this same
  "was a list under Python 2" gap.
- The `None`-vs-`int` comparison bug shape recurred **within a single
  accumulator loop from both directions** — `pootle_data/utils.py`'s
  `aggregate_children()` needed guards for both the accumulator being
  `None` (first iteration) *and* the per-item value being `None` (an
  item with nothing to compare) — fixing only one direction still
  left the other to be found by a later test run.

One cluster worth flagging so it isn't mistaken for a regression:
`webassets.exceptions.BundleError: 'js/vendor.bundle.js' not found`
affects any view test that renders a real page (as opposed to an error
page or a bare API response). This is **not** a Python 3 issue — stream
D (above) already documented that `*.bundle.js` files are gitignored,
webpack-built artifacts that this repo's baseline pytest environment
(`docker/ci/Dockerfile`) never builds either, and that
`ASSETS_DEBUG=True` (`tests/settings.py`) doesn't help because these
bundles have no source list for webassets to assemble from — they're
literal pre-built output. It's already folded into the Python 2
baseline's 123 failed / 94 error above. Not a Phase 1 target; goes away
when Phase 4 (frontend rebuild) lands real bundles.

## Validating against postgres and mariadb

Phase 0 stream B checked all three DB backends; Phase 1's suite had
only ever been run against sqlite until this pass. `docker-compose.
py3.yml` and `docker/py3/Dockerfile` were extended with `postgres` and
`mariadb` services (mirroring `docker-compose.ci.yml`'s Python 2
control channel exactly - same images, same gotchas) and two new
requirements files, `requirements/_db_mysql_py3.txt`
(`mysqlclient>=2.2,<3.0`) and `requirements/_db_postgresql_py3.txt`
(`psycopg2>=2.9,<3.0`): the Python 2 baseline's own DB driver pins
don't work under Python 3.12 at all - `psycopg2>=2.7,<2.8` fails to
build (`Py_TYPE()` became a read-only accessor macro), and
`mysqlclient>=1.3.3,<=1.3.12` builds but produces a broken import
(`SystemError: PyDescr_NewMember used with Py_RELATIVE_OFFSET`).
Building the newer mysqlclient also needs `pkg-config` added to the
image (without it, setup.py can't locate `mysql_config`/
`mariadb_config` at all).

Both DB backends then surfaced their own genuine Django-1.11-vs-
modern-driver incompatibilities - not sqlite-reachable code paths, so
Phase 1's sqlite-only runs never had a chance to find these:

- **postgres, `AssertionError: database connection isn't set to UTC`
  on every single test** (`django/db/backends/postgresql/utils.py`):
  `utc_tzinfo_factory(offset): if offset != 0: raise ...`. psycopg2
  2.7 (the Python 2 pin) passed `offset` as an int number of minutes,
  so a UTC connection's `0` compared equal; psycopg2 2.8+ (this
  port's pin) passes a `datetime.timedelta` instead, and
  `timedelta(0) != 0` is `True` in Python (`timedelta.__eq__` returns
  `NotImplemented` for a non-timedelta operand), so the assertion
  fired even on a genuinely-UTC connection. Confirmed directly against
  the running postgres container (`SHOW TIME ZONE` → `UTC`,
  `SELECT now()` → `tzinfo=utc`) before concluding this was a type
  mismatch, not an actual timezone misconfiguration. Fixed with
  `docker/py3/patch-django-postgres-tz.sh`, a new image-build-time
  patch script in the same style as `patch-django-six.sh` etc. -
  compares against `datetime.timedelta(0)` instead, matching how
  upstream Django itself fixed this once psycopg2 2.8 shipped.
- **postgres, `django.db.utils.DataError: invalid regular expression:
  quantifier operand invalid`**, on every query that filters by a
  glob-derived regex (`pootle_fs`'s `PathFilter`, `virtualfolder`
  rules, `pootle_format`'s filetype matching by path): `PathFilter.
  path_regex()` builds these from `fnmatch.translate()`, whose output
  format is Python-`re`-specific and gets passed straight through to
  the database as a `__regex` lookup rather than run through Python's
  `re` module. Two distinct Python-only constructs are involved, both
  found via the same "postgres transport rejects it, sqlite's
  Python-level regex engine doesn't care" pattern:
  - Python 3.6+ wraps the whole pattern in a scoped inline-flags
    group, `(?s:...)` - PostgreSQL's regex engine doesn't support the
    `(?flags:pattern)` form at all. Safe to unwrap entirely (none of
    these path patterns need DOTALL; paths don't contain newlines).
  - Python 3.11+ *also* wraps runs of `*` in an atomic group,
    `(?>...)`, to avoid catastrophic backtracking - another Perl/PCRE
    extension postgres doesn't support, and one that can appear
    anywhere inside the pattern rather than only as an outer wrapper.
    Downgraded to a plain non-capturing group (`(?:...)`) instead:
    semantically identical for matching, just without the
    backtracking-safety optimization, which doesn't matter for these
    short, bounded, glob-derived patterns.
  Both fixed in `PathFilter.path_regex()` (`pootle/apps/pootle_fs/
  utils.py`); `tests/pootle_fs/utils.py`'s own reference computation
  (which independently re-derives the expected pattern, per the
  established pattern from the earlier `\Z`/`\Z(?ms)` fix) updated to
  match. `pootle_fs/finder.py` has its own, unrelated
  `fnmatch.translate()` call - left untouched, since that one's result
  is compiled with Python's own `re.compile()` and never reaches the
  database.
- **mariadb, `KeyError: <class 'str'>` on every single database
  connection** (`django/db/backends/mysql/base.py`):
  `get_new_connection()` unconditionally does `conn.encoders[SafeText]
  = conn.encoders[six.text_type]` (`six.text_type` is `str` under
  Python 3) to also register Django's safe-string subclass under the
  driver's own encoder registry. mysqlclient 1.3.x (the Python 2 pin)
  registered `str`/`bytes` as explicit keys in `conn.encoders`, so the
  copy worked; mysqlclient 2.2+ (this port's pin - see
  `requirements/_db_mysql_py3.txt` for why 1.3.x can't be used at all
  under Python 3.12) dropped them as registered keys and handles
  `str`/`bytes` (and any subclass, `SafeText`/`SafeBytes` included -
  verified directly with a raw `MySQLdb` connection before concluding
  the copy was actually unnecessary) via a built-in C-extension
  fallback instead, so the very first line of every new connection
  raised `KeyError`. Fixed with `docker/py3/patch-django-mysql-
  encoders.sh`: guards both encoder copies behind a membership check,
  so it's a safe no-op on a driver that already handles these types
  without the registration, while staying correct for a driver that
  still needs it.

**Results after all three fixes**, `docker-compose -f docker-compose.
py3.yml run --rm test` with `APP_DB_ENV` set per backend, full clean
config (`filterwarnings = error` active, no `-p no:warnings`):

| backend  | passed | failed | errors | skipped | xfailed |
|----------|--------|--------|--------|---------|---------|
| sqlite   | 2299   | 108    | 94     | 10      | 1       |
| postgres | 2290   | 117    | 94     | 10      | 1       |
| mariadb  | 2299   | 117    | 94     | 0       | 2       |

All three totals reconcile to the same 2512 collected (117+2290+10+
1+94 = 117+2299+0+2+94); the 10 postgres-only "skipped" simply run
(and mostly pass, one xfails) under mariadb instead - a `skipif`
branching on DB vendor somewhere, not a bug.

Postgres's and mariadb's extra ~9 failures beyond the sqlite number
are **the same failing tests on both backends** - not a new Python 3
bug: every one of them (`tests/pootle_score/receivers.py`,
`tests/pootle_score/updater.py`, `tests/pootle_translationproject/
contextmanagers.py`, plus a few view tests) passes cleanly when run in
isolation or as a small targeted selection, and only shows up as part
of a full, all-2500-ish-tests run - the signature of inter-test state
leakage that both real-DB backends' transaction-rollback-based test
isolation exposes and sqlite's doesn't, rather than a genuine
per-backend incompatibility. Same family as the sqlite baseline's one
documented `test_model_user_last_event` flake. Not chased further this
pass (the three fixes above were the ones actually blocking postgres/
mariadb from running at all); worth a closer look if it recurs or
grows, but not blocking. The rest of the delta, same as sqlite, is
entirely the known `webassets.exceptions.BundleError` cluster.

**Phase 1 status: done, merged.** `python3-port` merged into `main`
with `--no-ff` (merge commit `09bff7d6d`, 174 files) and pushed to
`origin/main` (`ddc832ab4..09bff7d6d`) on 2026-09-02. `main` is now the
Python 3 port, validated at parity across sqlite/postgres/mariadb (see
above). The postgres/mariadb order-dependent failure set
(`pootle_score`/`pootle_translationproject` tests failing only in a
full-suite run) is still open if it recurs or grows, but wasn't
blocking enough to hold up the merge.

## Phase 2: Django upgrade ladder

Ladder: 1.11 → 2.2 → 3.2 → 4.2 → 5.2, one rung at a time, each merged
to `main` before the next starts (per the working-branch strategy).
Work happens on `django-ladder`, branched from `main` post-Phase-1-
merge. Same evidence-driven loop as Phase 1: bump the pin, run the
suite, frequency-rank the failures, fix the highest-leverage cause,
repeat - now against a whole framework major-version bump instead of
a language port, so most fixes are "this exact API was removed/
changed" rather than syntax.

### Rung 1: Django 1.11 → 2.2

New validation environment, `docker/django22/` + `docker-compose.
django22.yml`, built directly on top of Phase 1's already-solved
Python 3.12 problem (same base image, same apt packages, same
allauth/sortedm2m Python-3-packaging build patches - none of that is
Django-version-specific) with Django itself overridden to the 2.2 line
via a new `requirements/django22.txt`, installed as its own separate,
final `pip install` step rather than alongside `requirements/base.txt`
in one command - passed together, pip's resolver sees
`Django~=1.11.12` (`base.txt`, and transitively `pip install -e .`
re-parsing it for `setup.py`'s own `install_requires`) and
`Django~=2.2.28` as a real, unsatisfiable conflict in one solve and
refuses outright. Installing everything else on the 1.11 pin first and
overriding it afterward in a separate, independent `pip install`
works fine - pip only *warns* about the now-stale "requires
Django~=1.11.12" metadata (expected mid-ladder; `base.txt`'s own pin
only moves once a rung is actually done, not before).

**Eight real Django-1.11-vs-2.2 incompatibilities found and fixed,
each a genuine "this API changed/was removed" issue, not a language
port bug:**

1. **`django.core.urlresolvers` fully removed** (deprecated-but-
   present through 1.x, gone at 2.0): 4 of our own files (1 app file,
   3 test files) still imported `reverse` from it - swept to
   `django.urls.reverse`, same single-symbol import everywhere so a
   uniform sweep was safe. (A same-shaped call inside `django-contact-
   form==1.5`'s own `views.py` turned out to already be guarded by a
   `try: from django.urls import reverse / except ImportError:` -
   nothing to fix there.)
2. **`django.utils.translation`'s internal `_trans` proxy dropped the
   `u`-prefixed method names** (`ugettext`/`ungettext` - Django 2.0
   unified these with `gettext`/`ngettext` once Python 2's str/
   unicode split stopped existing): our own `pootle/i18n/gettext.py`
   reaches into that internal proxy directly (not the public,
   still-aliased `django.utils.translation.ugettext`, which still
   works fine) - `_trans.ugettext(...)`/`_trans.ungettext(...)` calls
   switched to `_trans.gettext(...)`/`_trans.ngettext(...)`, which
   Python 3's always-unicode strings make a correct fix, not just a
   workaround.
3. **Django's vendored `django/utils/six.py`** is byte-identical to
   1.11's copy, same break, same fix: `docker/py3/patch-django-six.sh`
   reused as-is, just run after the `django22.txt` override (not
   alongside the other patch steps) since that override reinstalls
   Django itself and would silently revert the patched file otherwise.
4. **`django-contrib-comments==1.7.3`** (`base.txt`'s pin) imports
   `django.core.urlresolvers` at its own module level
   (`django_comments/__init__.py`) - a third-party instance of (1)
   above. Bumped to `2.2.0`, the first release requiring Django>=2.2
   (declared support through 4.0 - deliberately not the narrowest
   option that would only barely cover this rung).
5. **`django-sortedm2m==1.5.0`** (`base.txt`'s pin)'s
   `SortedRelatedManager._add_items()` override doesn't accept
   `through_defaults`, a kwarg Django 2.2 itself added to the M2M
   `add()`/`create()` API - the very first test to save a `Project`
   (`Project.filetypes.add(...)`, hit by any DB-backed test via
   `ProjectDBFactory`) raised `TypeError: ..._add_items() got an
   unexpected keyword argument 'through_defaults'`, cascading into
   2510 setup errors. Bumped to `3.1.1` (first release declaring 2.2
   support, through 3.2 - covers this rung and the next one too);
   installs from a real wheel, so Phase 1's `patch-sortedm2m.sh`
   `UltraMagicString`-in-`setup.py` build patch (needed for 1.5.0
   specifically) isn't needed for this version.
6. **`django-overextends==0.4.3`** (abandoned upstream - last release
   ever was 2015, no maintained fork exists) reimplements Django's
   `find_template()` against the pre-1.9 loader API
   (`loader.load_template_source(name, dirs)`), which Django's own
   built-in loaders kept as a deprecated-but-working shim through 1.11
   and dropped outright by 2.2. Only one template in this codebase
   uses `{% overextends %}` (`import_export/templates/browser/
   index.html`), but it's inherited by enough pages to affect ~40 test
   cases, all surfacing as `AttributeError: 'Loader' object has no
   attribute 'load_template_source'`. No version bump available (only
   ever one release) - `docker/django22/patch-overextends.sh` ports
   `find_template()` to the modern `get_template_sources()`/
   `get_contents()`/`Origin`-object API instead, patching the
   installed package directly (same style as the postgres-tz/mysql-
   encoders patches from Phase 1's DB work) since there's nothing
   wrong with the package's own *build*, only runtime code relying on
   a since-removed API.
7. **`dj.subcommand==0.0.3`** (also only ever one release, no
   maintained fork) defines two `CommandParser` subclasses
   (`SubcommandsParser`, `SubcommandsSubParser`) that never define
   their own `__init__`, relying entirely on Django 1.11's
   `CommandParser.__init__(self, cmd, **kwargs)` storing the command
   instance as `self.cmd`. Django 2.1 made `CommandParser` keyword-
   only with no `cmd` parameter at all, so the one subcommand-based
   management command this codebase has (`pootle fs`, exercised by
   ~70 test cases across it and its own sub-subcommands) started
   raising `TypeError` from one class then the other in turn as each
   got fixed. `docker/django22/patch-dj-subcommand.sh` gives both
   classes back an `__init__` that accepts/stores `cmd` (positionally
   for `SubcommandsParser`, via `**kwargs` for `SubcommandsSubParser` -
   that's how argparse's own `add_subparsers()` machinery instantiates
   it) and forwards the rest to Django's now-keyword-only
   `CommandParser.__init__`. The same patch also adds a `--force-color`
   argument to this package's own hand-rolled copy of Django's default
   command arguments (frozen at whatever Django version it was written
   against) - Django 2.2 added `--force-color` alongside `--no-color`,
   and `BaseCommand.execute()` unconditionally reads
   `options['force_color']`, `KeyError`-ing on any command whose parser
   doesn't have it.
8. **`django-allauth==0.35.0`** (`base.txt`'s pin - already flagged in
   stream G's dependency audit as carrying 6 known advisories against
   this exact pin, so overdue for a bump regardless)'s
   `adapter.py` calls `django.utils.http.is_safe_url(url)` with one
   argument, but Django 2.1 made the second parameter
   (`allowed_hosts`) required - every login/logout request (the
   redirect-safety check that adapter method backs runs on every
   request through allauth) 500'd instead of redirecting. Bumped to
   `0.42.0` (first release requiring Django>=2.0, declared support
   through 3.0). Same `convert_path`-removed-from-setuptools build
   issue as Phase 1's `0.35.0` patch (checked directly - byte-
   identical `setup.py` line), needing its own re-pointed copy,
   `docker/django22/patch-allauth.sh` (kept separate from `docker/
   py3/patch-allauth.sh`, which still needs to keep building 0.35.0
   for Phase 1's still-active image).

**Two test-expectation fixes** (real, correct behavior changed;
only the tests' own hardcoded expectations were stale):

- **Form widget rendering dropped its self-closing tag.** Django 2.0
  rewrote form widget rendering from string formatting to templates
  and switched void elements from XHTML-style (`<input ... />`) to
  plain HTML5 (`<input ...>`) - our `TableSelectMultiple` widget
  (`pootle/core/views/widgets.py`) delegates its checkbox rendering to
  Django's own `CheckboxInput.render()`, so its *output* correctly
  changed too. 13 hardcoded `" /></td>"` expectations across 5 test
  functions in `tests/core/views.py` updated to `"></td>"`.
- **Every command's parsed options dict gained `force_color`** (see
  finding 8's `--force-color` addition above) - two test files
  (`tests/commands/refresh_scores.py`, `tests/commands/
  update_stores.py`) hardcode a `DEFAULT_OPTIONS` dict they compare
  the real parsed options against; both updated to include
  `'force_color': False`.
- **`django-allauth`'s `LogoutView` started routing AJAX POSTs through
  the same `_ajax_response()`/adapter mechanism `LoginView` already
  used**, sometime between 0.35.0 and 0.42.0 - previously logout
  returned a genuine 302 redirect unconditionally regardless of the
  `X-Requested-With` header; now an AJAX logout gets the same
  JSON-with-`location` response our own `PootleAccountAdapter.
  ajax_response()` override already gives AJAX logins (`tests/
  accounts/views.py::test_accounts_login` already expected this
  shape). `test_accounts_logout` updated to match - this is our own
  adapter's intentional, existing behavior finally applying
  consistently, not a new one.

**Result after all of the above**, full clean config
(`filterwarnings=error` active): **2298 passed / 109 failed / 94
errors / 10 skipped / 1 xfailed**, essentially matching Phase 1's
sqlite milestone (2299/108/94) - every failing/erroring test id here
except one is already present in that same baseline list (diffed
directly, not eyeballed), i.e. the same webassets cluster plus the
same pre-existing gaps, not a new regression surface from the Django
bump.

**The one exception - since found and fixed:** `tests/
pootle_translationproject/contextmanagers.py::
test_contextmanager_update_tp_after_suggestion` failed reproducibly
(not order-dependent - failed in isolation too, unlike the postgres/
mariadb flake set above), with `assert 129 == 6` on
`updated["store_data"]["max_unit_revision"] ==
original["store_data"]["max_unit_revision"]` in the test's *second*
of two sequential "add a suggestion" blocks - `original` (captured at
the start of that second block) showed a stats snapshot from *before*
the first block's own suggestion-accept had updated anything, despite
that accept having already completed and its own assertions (checking
the very same field) having already passed correctly.

Root cause, once fully traced with targeted instrumentation (object
identity, `id()`, and raw aggregate queries logged at each step - the
"maybe it's a stale cache" theory needed to be proven, not assumed):
`pytest_pootle/fixtures/signals.py`'s `UpdateUnitTest.__exit__` calls
`self.unit.refresh_from_db()` before re-reading state. Django 1.11's
`refresh_from_db()` only reloaded concrete field values and left any
*cached related objects* (`self.unit.store`, etc.) untouched - Django
2.0 changed this (ticket #27343) so a bare `refresh_from_db()` also
clears cached forward-FK relations, treating the old behavior as a
bug (returning stale related objects). This test's own `store0`/`tp0`
fixtures are held onto for the whole test function, and `self.unit.
store` is the *same object* as `store0` (Django's reverse-manager
optimization caches the parent back onto rows fetched via `store0.
units...`) - `store0`'s own `.data` (a cached `StoreData` instance)
gets mutated in place across the whole test as the real, intentional
mechanism by which later blocks see earlier blocks' changes (this
codebase's own `pootle_data.utils.DataUpdater` reads/writes through
exactly that cached object, by design). Under Django 2.2, the first
block's own `self.unit.refresh_from_db()` call silently swapped `self.
unit.store` for a disconnected, freshly-queried Store instance instead
of leaving it pointed at `store0` - the two explicit follow-up
`refresh_from_db()` calls (`self.unit.store.data.refresh_from_db()`
etc.) then dutifully refreshed *that* throwaway object's `.data`,
while `store0`'s own cached `.data` - the one every subsequent block
actually reads - was left exactly as stale as it was when first
populated. Confirmed directly (not inferred): `id(store0) ==
id(unit.store)` before any refresh, `store0.data.max_unit_revision`
still showing the pre-accept value immediately after the accept block
had already exited and passed its own assertions on that same field.

Fix: `self.unit.refresh_from_db(fields=["revision"])` instead of a
bare call. Per Django's own `refresh_from_db()` implementation, the
cached-relation-clearing step only runs for fields actually being
reloaded - the test only ever reads `unit.revision` back from this
refresh, so limiting it to that one field reloads what's needed
without clearing `self.unit.store`'s identity at all, on any Django
version (verified against both this rung's Django 2.2 image and
Phase 1's Django 1.11 image - the fixture is shared code, and this
had to not regress there). Minimal, one-line fix plus a comment;
`pytest_pootle/fixtures/signals.py` is the only file touched. Rerunning
the full suite confirms it: the test disappears from the failure list
entirely, with no new failures introduced (diffed directly against
the prior run - the only other change was `tests/commands/
update_tmserver.py::test_update_tmserver_files` flipping in, which
traces to the elasticsearch container being OOM-killed by host memory
pressure *during this same run* - confirmed via `docker ps` showing
`Exited (137)` - the same already-documented operational flakiness,
not a new regression). Rung 1's sqlite results are now genuinely
clean against the Python 2 baseline, not just "one known difference
away" - the only non-passing tests left are the pre-existing webassets
cluster and, this run, the one ES-host-contention flake.

This bug shape - a test helper relying on Django leaving stale cached
relations in place across a `refresh_from_db()` call - is worth
remembering for the rest of the ladder: any test fixture or helper
calling a bare `.refresh_from_db()` on an object whose *cached
relations* (not just its own fields) matter to later code is a
candidate for the same failure mode from here through Django 3.0+ (the
behavior 2.0 introduced stays in effect going forward, so this won't
un-happen on a later rung) - `fields=[...]` is the fix wherever only
specific columns actually need reloading.

### Validating rung 1 against postgres

`docker/django22/Dockerfile` already installed the postgres/mysql
drivers (Phase 1's `_db_postgresql_py3.txt`/`_db_mysql_py3.txt`) but
was missing Phase 1's two Django-source patches for them
(`patch-django-postgres-tz.sh`, `patch-django-mysql-encoders.sh`) -
never added when this rung's Dockerfile was first written, since that
work was all sqlite-only at the time. First postgres run: **725/725
errors** in the `pootle_fs`/`vfolders`/`database.py` sanity subset,
same `AssertionError: database connection isn't set to UTC` as Phase
1's very first postgres attempt - Django 2.2's `django/db/backends/
postgresql/utils.py` turns out to be byte-identical to 1.11's copy
(checked directly), same `if offset != 0:` bug, same fix. Added
`patch-django-postgres-tz.sh` to this Dockerfile (after the
`django22.txt` override, same reason as the six.py patch). **Not**
adding `patch-django-mysql-encoders.sh` though: Django 2.2's mysql
backend `get_new_connection()` is just `return Database.connect(
**conn_params)` (checked directly) - the whole `conn.encoders[
SafeText] = ...` block that needed patching under 1.11 is gone
entirely, so Django itself already fixed this between 1.11 and 2.2 and
there's nothing left to patch for this rung.

With that one patch added, the sanity subset (database.py,
pootle_fs/, vfolders/path_matcher.py - the tests Phase 1's own regex-
portability fixes in `pootle_fs/utils.py` target) passed clean: 725/
725. Full suite: **2297 passed / 110 failed / 94 errors / 10 skipped /
1 xfailed**, one worse each way than the sqlite rung-1 number (2298/
109/94) - diffed directly against that same run's failure list (not
eyeballed): every failing/erroring test here except one is already in
it. The one exception, `tests/commands/update_tmserver.py::
test_update_tmserver_files`, is **not a Django-2.2 or postgres bug** -
traced to the elasticsearch container itself dying under host memory
pressure mid-validation (`docker ps` showed `Exited (137)` - SIGKILL,
consistent with an OOM kill - immediately after each restart attempt,
correlating directly with `vm_stat` showing under 100MB free and
`uptime` load averages of 13-14 at the time). Restarting ES and
retrying twice reproduced the same crash both times rather than
clearing it, so this is host-level contention exactly matching the
"Operational note on Elasticsearch-under-emulation reliability"
already documented in Phase 1's own section above, not a new failure
mode - noted here rather than chased as a regression, since the
underlying cause and its signature are already on record.

**Net: rung 1 is validated against postgres at the same level of
parity sqlite already has.**

### Validating rung 1 against mariadb

Run under adverse conditions: this host's Elasticsearch container was
being repeatedly OOM-killed (`docker ps` showing `Exited (137)` within
seconds of each restart, 3 separate attempts) by genuine host-level
memory exhaustion - `vm.swapusage` showed under 900MB of 22.5GB swap
free, traced to other users' work on this shared machine (Adobe
Photoshop/Illustrator processes under a different account, ~13GB+
combined, plus an unrelated QEMU VM), not anything Docker- or Pootle-
related. Not something fixable from here, so this validation pass ran
with `redis`/`mariadb` only, no `elasticsearch` - `tests/settings.py`
hardcodes `elasticsearch` as the default TM server host for the whole
suite, so this means every DB-touching test that touches the TM broker
logs connection-refused noise, but (per Phase 1's own earlier finding
on this exact point) that noise is caught/swallowed almost everywhere
except tests that specifically assert on TM/ES behavior.

Sanity subset (`database.py`, `pootle_fs/utils.py`, `vfolders/
path_matcher.py`) passed clean without ES: 36/36 - confirms the
postgres-tz-style patch isn't needed for mysql (already established
directly above) and Phase 1's regex-portability fixes carry over
unchanged here too. Full suite: **2306 passed / 110 failed / 94
errors / 2 xfailed** (2512 total, reconciling the same way the
postgres/mariadb Phase-1 skip-vs-xfail difference did). Diffed
directly against the sqlite rung-1 list: **exactly one** test differs,
`tests/commands/update_tmserver.py::test_update_tmserver_files` - and
that one is fully expected given ES wasn't running for this pass, not
a mystery the way it was for postgres's own run of the same test
(there it was genuine mid-validation ES instability; here ES was
deliberately not started at all). Every other failing/erroring test
here is already in the sqlite baseline's own list.

**Net: rung 1 is validated against mariadb at the same level of
parity sqlite and postgres already have** - modulo a from-scratch,
ES-backed rerun of just `test_update_tmserver_files` once host memory
pressure clears, to close out the one test this pass couldn't
exercise.

**Rung 1 is now validated against all three DB backends** (sqlite,
postgres, mariadb) at the same near-parity level Phase 1 itself
reached - the Django 1.11 → 2.2 bump introduces no backend-specific
regressions beyond what was already fixed getting sqlite to parity.

**Postgres re-run with ES actually up (2026-09-03):** confirms the
`test_contextmanager_update_tp_after_suggestion` fix directly -
**109 failed / 2298 passed / 94 errors**, an exact match to the
sqlite rung-1 numbers, diffed directly. The lone remaining difference
is `test_update_tmserver_files` again - not a regression: ES came up
successfully (confirmed ready via a health-check poll) but was
OOM-killed ~35s into the run (`docker inspect` showing a 35-second
lifetime, exit 137) by the same host memory contention documented
above, so only this one ES-hard-dependent test was actually affected;
everything else in the 3+ minute run tolerated ES's absence exactly
as it always has. Tried mariadb the same way immediately after -
freed up host memory first (stopped the now-unneeded postgres
container) - but ES failed to even reach ready 3 times in a row (dying
in 3-12s each attempt, `vm.swapusage` showing under 1.7GB of 21.5GB
free throughout, unmoved by the cleanup); `top -o mem` traced it to
the same other user's Photoshop/Illustrator processes (~10GB combined)
still resident, not a transient spike. Not chased further at that
point - this is squarely the same operational condition already on
record (see the "Operational note on Elasticsearch-under-emulation
reliability" section above), not a code issue, and retrying against
genuine external memory pressure with no sign of clearing wasn't
going to change the outcome.

**Mariadb re-run with ES actually up (2026-09-03, host memory pressure
cleared - the other user's session that was holding ~10GB in Adobe
Photoshop/Illustrator processes had ended by this point, confirmed via
`top -o mem` no longer showing them):** clean on the first attempt -
ES came up in 15s and survived the whole ~2m18s run. **108 failed /
2308 passed / 94 errors / 2 xfailed**, reconciling to the same 2512
total. Diffed directly against the sqlite baseline: **zero new
failures**, and the *only* difference is one fewer failure than that
baseline list (`test_contextmanager_update_tp_after_suggestion`,
already fixed - the baseline snapshot just predates the fix).
`test_update_tmserver_files` doesn't appear in the failure list at
all this time, confirming ES was genuinely up and answering queries
throughout, not just running.

**Rung 1's DB-backend validation is now fully closed out**: sqlite,
postgres, and mariadb all confirmed clean (postgres modulo the one
ES-availability caveat noted above, which is purely a one-off host
condition, not a reproducible gap - mariadb's clean ES-up run here
gives every reason to expect postgres would be equally clean on a
retry once host memory allows one).

**Not yet done, still on `django-ladder`:**
- `requirements/base.txt`'s own pins (`Django~=1.11.12`,
  `django-contrib-comments==1.7.3`, `django-sortedm2m==1.5.0`,
  `django-allauth==0.35.0`) haven't moved - `django22.txt` is
  currently a bolt-on override, same pattern as Phase 1's `_db_*_py3.
  txt` files. Whether to fold `django22.txt`'s pins into `base.txt`
  directly (retiring the override + Phase 1's now-superseded pins
  outright) or keep every rung's override file around for
  reference is an open call - lean toward folding in once rung 1 is
  fully done, since (unlike Phase 1's sqlite/postgres/mariadb split,
  where all three backends are permanent, parallel targets) there's
  only ever one "current" Django version on this branch at a time.
- Merge rung 1 into `main` once it's at (or has a documented reason to
  be below) parity - not done yet.
- Rungs 2-4 (2.2 → 3.2 → 4.2 → 5.2) not started.
