# Implementation and executed checks

## CI run #1 repair

Inspected actual job logs for run 40350955406, Docker job 121670582025. Its exit
127 is confirmed at the original isolation-script line 89: env -i excludes
/usr/sbin from PATH, while the test called bare runuser. The production supervisor
had already succeeded using /usr/sbin/runuser. Test commands now use that absolute
path, with an early in-image executable/identity-switch preflight. No package
installation or relaxation of isolation is needed.

Added precise command/file/line/status ERR diagnostics and LF Git attributes,
plus tests that preserve exit 127/1 and do not expand a synthetic secret into
logs. Corrected an unreadable /proc environment being treated as empty: actual
backend requests now enforce the environment allowlist and reject pollution.

Local results: four shell-diagnostic/path/line-ending tests PASS; safe-preview HTTP
tests including unexpected environment rejection PASS; changed PHP lint, Bash
syntax and whitespace review PASS. Full corrected Docker run NOT EXECUTED locally
(Docker unavailable). The original GitHub run passed the PHP job, Docker build,
synthetic production flows/TLS, instructor gate, and UID assertions, but the full
isolation gate did not finish. Real independent training DB grants remain unverified.

## GitHub Actions automation

Added `.github/workflows/isolation.yml` with read-only, PR/manual Linux jobs for
PHP 8.3 regressions and `tests/container-isolation.sh`. The Docker gate now provides
a fresh TLS-enabled MySQL fixture and synthetic accounts, so it can test homepage
queries and real login/session/admin flows rather than only startup without a DB.
Added `tests/container_http.py`, `tests/fixtures/container-users.sql`, and
`docs/ci-isolation.md`; made tests/integration.py initialize MariaDB on Linux and
use explicit TCP rather than localhost sockets. The production Dockerfile and CA
startup behavior are unchanged by this CI addition.

Local checks pass for YAML parsing/policy, shell/PHP syntax, byte checks, throttling,
safe-preview HTTP, and the full synthetic TLS regression suite including the new
HTTP helper. Actual GitHub Actions/Docker execution has NOT run yet. No push,
workflow dispatch, Render deploy, or live database action was performed.

## Infrastructure review follow-up

Reviewed the original 21 changed/new files. Added tests/container-probes.php for
stronger Docker assertions, bringing the current change set to 22 files.

Issues found and fixed:

- Removed the global client-IP login bucket: Render/NAT shared proxy addresses
  could previously pool unrelated users into a 600-request budget. Throttling is
  now per account only; 650 unrelated accounts pass independently. Account-level
  lockouts and storage failure/capacity limits remain explicit availability risks.
- Qualified every setup/reset write with pc_forge_training. A SQL client that
  continues after an error cannot redirect those statements into its active
  pc_forge/mens_daydb schema. The regression runs against disposable local
  sentinels under both protected names and confirms they remain unchanged.
- Moved the proxy token from inherited environment to a protected runtime file.
  Added env -i after runuser/PAM as well as before it, so PAM cannot reintroduce
  unexpected environment values. The startup probe verifies an environment
  allowlist and rejects membership in the production www-data group.
- Expanded the previously incomplete Docker gate: live worker UIDs, production
  CA ownership/readability, actual production secret/session-file denial, forged
  training admin cookies under both cookie names, private production session
  configuration, disabled-route/source denial, missing-instructor startup failure,
  and supervisor shutdown after backend exit. Requests have bounded timeouts.
- Credential independence checks are explicitly synthetic markers only. The gate
  reports real database credentials/TLS/grants as NOT VERIFIED. The preview has
  no database credentials; vulnerable authentication remains absent.

Executed again: all PHP syntax/BOM checks, Bash syntax, throttle/source-policy
unit checks, preview HTTP checks, disposable Apache authentication/proxy checks,
the complete production regression suite over local TLS, SQL namespace-safety
fixtures, and Git whitespace review. All passed. Docker is unavailable and no
Linux isolation check is marked PASS. No live server/database was contacted.

**Deployment verdict: not yet ready for production sign-off.** Run the Linux
Docker gate and validate representative mount permissions/startup behavior before
deploying these Docker/startup changes, even with preview disabled. Keep training
off and do not implement vulnerable authentication until isolation/grants are
verified. No Git commit/push or Render deployment was performed.

## Completed scope

Implemented safe single-service proxy/process scaffolding and a visual preview,
with training disabled by default. No vulnerable authentication, real training
login, training brute-force runner, executable XSS, CSRF bypass, IDOR or broken
authorization is implemented. Those remain blocked by missing verified Linux
isolation and independent database provisioning. This implements the requested
safe fallback; it is not a claim that the full vulnerable environment is complete.

Production login now has server-side throttling. Native PDO prepares, password
verification, CSRF, redirects, role checks and the existing CA copy/verification
remain. No public training navigation was added. Production records, passwords,
admin ID 1, and mens_daydb were not changed or queried.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| PHP syntax, every PHP file | PASS | XAMPP PHP 8.2.12 |
| PHP BOM/leading-output checks | PASS | tests/php_source.py |
| Startup/supervisor/container-test Bash syntax | PASS | Git Bash -n |
| Production per-account throttle, expiry, corrupt-storage failure | PASS | tests/training_checks.php |
| Production existing auth/admin/cart/checkout suite | PASS | Disposable MariaDB fixtures over verified TLS |
| Production prepared login rejects SQL-injection payload | PASS | Actual HTTP request to isolated fixture |
| Shared-proxy IP cannot pool unrelated account budgets | PASS | 650 distinct accounts admitted independently |
| Production HTTP 429 and new-session resistance | PASS | 15 admitted attempts, next rejected with Retry-After |
| Safe storefront/login rendering with existing CSS | PASS | tests/training_http.py |
| Preview direct access, cookie/auth rejection | PASS | Actual PHP HTTP responses |
| Preview authentication absent, no auth cookies emitted | PASS | POST returns 503; no Set-Cookie |
| Generated Apache proxy config syntax | PASS | Disposable XAMPP Apache fixture |
| Instructor required before proxy request | PASS | Unauthorized HTTP 401; fixture backend not contacted |
| Cookie/authorization removal at proxy | PASS | Actual backend inspected received headers |
| Backend Set-Cookie removed | PASS | Actual client response inspected |
| Forwarded HTTPS required | PASS | Valid instructor without HTTPS header rejected HTTP 403 |
| No public navigation training link | PASS | Source assertion; layout unchanged |
| Git diff whitespace | PASS | git diff --check |
| Docker image and Linux supervision/UID isolation | NOT TESTED | Docker unavailable; WSL not installed |
| Actual mounted secrets and foreign process environ isolation | NOT TESTED | Linux probes implemented; not executed locally |
| Separate training sessions/filesystem runtime permissions | NOT TESTED | Provisioned in startup; requires container test |
| Real training DB privileges/TLS | NOT TESTED | No training credentials/server supplied; no DB connection in preview |
| Training setup/reset SQL with protected active-schema fixtures | PASS | Qualified writes leave local pc_forge/mens_daydb sentinels unchanged; never run live |
| Vulnerable SQL injection / bounded training brute force | NOT IMPLEMENTED | Explicitly blocked pending isolation verification |
| Live Render/Aiven and production PHP 8.3 runtime | NOT TESTED | No deployment/live connection attempted |

Initial Apache invocation was blocked by sandbox filesystem restrictions. Repeating
the disposable test outside the sandbox passed; existing Apache configuration was
not edited. No test failed in the final executed local checks. The container test
is provided as tests/container-isolation.sh, but has not run and may reveal further
deployment-specific issues that must be fixed before enabling even the preview.

## Files changed

Modified:

- Dockerfile
- .dockerignore
- .htaccess
- docker/start-pc-forge
- login.php
- tests/integration.py

Added:

- config/login_limit.php
- docker/prepare-training.php
- docker/training-config.php
- docker/training-router.php
- docker/verify-training.php
- docker/supervise-pc-forge
- training-src/public/index.php
- training-src/database/setup.sql
- training-src/database/reset.sql
- training-src/README.md
- training-src/TEST_RESULTS.md
- tests/training_checks.php
- tests/training_http.py
- tests/apache_training.py
- tests/container-isolation.sh
- tests/container-probes.php

## Required next steps (manual)

1. Run tests/container-isolation.sh in Linux with Docker, curl and OpenSSL. Check
   actual UID/process/secret protections and normal public routes in staging.
2. Keep preview disabled by default. To enable only the safe preview after review,
   supply instructor configuration described in README and verify HTTPS behavior.
3. Independently provision synthetic DB and reader grants, validate TLS and denied
   production privileges. Do not reuse production credentials or configure any
   vulnerable backend yet; there is none in this implementation.
4. Only after these boundaries are verified should a subsequent implementation
   add restricted SQL injection, instructor-bound expiration and attempt budgets,
   audit storage, session-cookie allowlisting, and controlled comparisons.

No Git commit/push, Render deploy/config change, or live DB action occurred.
