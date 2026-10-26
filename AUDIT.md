# PC Forge audit and repair

## Headers/session repair follow-up

Production logs for deployed commit `b70cd1507797813c0feae26e0d2b702a9b86e970`
identify output starting at `config/db.php:1`. Byte inspection confirmed a leading
newline (`0A 3C 3F 70 68 70`), not a BOM, before the PHP opening tag. Removing that
single byte fixes the confirmed source of premature output without changing DB
logic. The earlier blank-page investigation below describes the earlier audit;
the new production evidence identifies this specific headers/session failure.

All 12 PHP files were scanned for leading output and UTF-8 BOMs. None remain;
PHP-only files have no closing tags. Bootstrap now configures and starts the
session before requiring DB helpers and before starting its existing page-render
buffer. Buffering is retained only for safe rendering of later errors, not to
hide startup output. Cookie security, CSRF, PDO prepares, TLS verification,
certificate paths, and production logging are unchanged.

Regression checks are `python tests/php_source.py` and the existing isolated
`tests/integration.py` suite, now with PHP output buffering disabled, a quiet DB
include check, a session startup check, and a check that HTTP logs contain no
headers/session initialization warnings. The suite uses temporary accounts and
database fixtures only; it does not reset/recreate production admin ID 1.

Follow-up results: PASS for all 12 PHP byte scans and syntax checks, session startup
with automatic buffering disabled, Render HTTPS Secure/HttpOnly/SameSite flags,
the complete isolated HTTP regression suite (including homepage, registration,
login, admin access, redirects, session persistence, logout, checkout, and safe
errors), no header/session warnings in regression logs, startup shell syntax,
local Apache configuration syntax, and Git whitespace checks.

Available runtime: PHP 8.2.12; PHP 8.3 and Docker are unavailable locally. Local
Apache default configuration validates; container execution and live Render/Aiven
connectivity are not claimed. No Render deployment or settings change is triggered
by this repair; pushing the fix may invoke the service's existing automatic deploy.

Audit date: 2026-10-26 (Asia/Manila). Changes are local; nothing was pushed,
deployed, or changed in Aiven. No existing accounts or passwords were changed.

## Blank-page diagnosis

Confirmed in the repository baseline: login always redirected to `index.php`,
including for admins. That page performed database queries before rendering any
HTML. There was no application exception handler, while production correctly
disabled PHP error display. A database/configuration/query exception therefore
returned an effectively blank HTTP 500 response.

Reproduction used the HEAD baseline files in a temporary local PHP server with
`display_errors=0` and missing DB configuration. The response was HTTP 500 with
one byte of whitespace. The repaired application was tested with a deliberately
unavailable table in an isolated database: it returned HTTP 500 with a safe,
visible error page and private diagnostics.

This confirms the code path that causes blank pages, **not the specific database
failure on Render**. The production URL could not be accessed by the browsing
tool, and production logs/live schema were unavailable. The failing SQLSTATE and
driver code in Render logs are needed to distinguish schema drift, configuration,
connectivity, permissions, or another runtime failure. No live login was attempted.

## Authentication findings and repairs

- Registration previously collapsed validation, duplicate-email, schema, and
  connectivity failures into one unlogged message. It now validates name/email/
  password lengths, handles MySQL duplicate email code 1062, logs unexpected
  failures safely, and explicitly inserts the `customer` role. Form fields cannot
  create an admin account. Passwords use PHP password hashing/verification;
  `VARCHAR(255)` in the repository schema is sufficient for hashes.
- Login previously mislabeled all exceptions as invalid credentials. Expected
  credential errors now receive a validation response; infrastructure errors
  receive a generic HTTP 500 response with private diagnostics. Successful login
  regenerates the session ID, drops the password hash, rotates the CSRF token,
  and redirects admins to `admin/index.php`, customers to `index.php`.
- Sessions use strict mode, cookies only, HttpOnly, SameSite=Lax, and Secure over
  HTTPS (including Render's forwarded HTTPS header when `RENDER=true`). Failure
  to start a session becomes a visible safe HTTP 500 rather than silent failure.
- Admin access is checked before any admin action, using the current database
  role. Revocation takes effect even for an existing session. Customers receive
  HTTP 403; anonymous requests are redirected to login.
- Logout now requires POST plus CSRF, clears session state, expires the cookie,
  and destroys the server session. The existing navigation contains that form.
- CSRF verification rejects missing tokens, array input, and expired tokens.
  Output encoding is retained. Includes resolve relative to their own files.

## Application and security repairs

- Bootstrap supplies safe exception/fatal handling and appropriate HTTP 500
  responses. Validation errors receive HTTP 422. Diagnostics record context,
  exception class, SQLSTATE/driver codes, route basename, file basename, and line;
  raw messages, SQL, request values, connection strings, and secrets are omitted.
  Error output remains disabled. Responses disable caching and set nosniff and
  referrer-policy headers.
- Cart supports quantity updates and validates stock/quantity limits server-side.
  Removed/inactive products are pruned on cart display; checkout also revalidates
  all products. Cart mutations invalidate previously rendered checkout forms.
- Checkout validates shipping field lengths, phone, payment method, and a
  session-bound submission token. Product locks are taken in ID order, inventory
  and orders/payment records remain in one transaction, totals accumulate in
  integer cents, and failures roll back. Session locking and clearing the cart
  after commit prevent duplicate submissions in the same session. Stale forms
  cannot order a newly changed cart. This is not a distributed idempotency service.
- Admin validates product price, stock, existing category, and HTTP(S) image URLs.
  Order status changes lock the order. Cancelling pending/processing orders restores
  inventory transactionally once; cancelled orders cannot be reopened, delivered
  orders cannot be cancelled, and shipped orders can only advance to delivered.
  Existing already-cancelled orders are not retrospectively modified or restocked.
  Payment status remains a manual bookkeeping action: cancellation does not issue
  a refund or automatically label money as refunded.
- Apache rules disable directory listings and deny hidden paths, SQL/config/PEM/
  key/log/Markdown files, Dockerfile, and internal PHP entry files. Config,
  database, docker, and tests directories deny direct HTTP access. Docker excludes
  tests, audit docs, PEM/private-key files, and agent metadata. Application source
  is owned by root, preventing Apache workers from modifying it.

## Database compatibility and data preservation

Queries were reviewed against every table in `database/schema.sql`. The isolated
suite imports that schema and exercises native PDO MySQL prepares and verified
TLS against MariaDB 10.4.32. IDs, relationships, enum values, unique email,
unique payment/order relationship, password capacity, stock, and decimal columns
match the application. Transactional tables must use InnoDB in production.

`addresses` and `cart_items` are present but not used by the current session-cart
and inline-shipping flow. This behavior is preserved. No schema migration is
required by these changes. **Do not reimport schema.sql into production.**

The live Aiven schema has not been compared. `database/inspect.sql` is a read-only
metadata inspection scoped to `pc_forge` for an authorized SQL client. Compare
its results with schema.sql before proposing any migration. It does not read or
write `mens_daydb`, and no tests or application repairs were run against Aiven.

## Test results

| Check | Result | Evidence / limits |
| --- | --- | --- |
| Every PHP file syntax | PASS | Local PHP 8.2.12; target remains PHP 8.3 |
| Original blank-response reproduction | PASS | Baseline HTTP 500, one byte, missing DB config |
| Registration, hash storage, forced customer role | PASS | Isolated HTTP + MariaDB fixtures |
| Duplicate email and incorrect password | PASS | Safe HTTP 422 responses |
| Customer/admin login redirects and session regeneration | PASS | HTTP Location and cookie assertions |
| Admin GET/POST restrictions and live-session demotion | PASS | Anonymous redirect, customer HTTP 403 |
| Logout and session invalidation | PASS | POST/CSRF checks, protected route after logout |
| Products, empty category, cart add/update/remove/stock/CSRF | PASS | Real queries against disposable schema |
| Checkout, ownership-scoped order history, manual payment | PASS | Persisted order, line, payment, and inventory assertions |
| Checkout invalid address, stale form, duplicate submission | PASS | Rejected or redirected; one successful order |
| Inventory race safeguards | PASS (serial regression) | FOR UPDATE stock recheck and transaction rollback; no concurrent load test |
| Failure after order/stock writes | PASS | Missing payments table triggers rollback of order, lines, and stock |
| Admin product, stock, order, payment actions | PASS | Isolated HTTP fixtures; unsafe image URL rejected |
| Cancellation restores inventory once | PASS | Transactional restoration; reopening rejected |
| Missing/invalid DB and SSL configuration | PASS | Separate PHP processes; generic errors |
| Verified TLS used by test database connection | PASS | Generated disposable certificate; nonempty negotiated SSL cipher |
| Unexpected query failure | PASS | Safe nonblank HTTP 500, no SQLSTATE/path in body |
| Startup script shell syntax | PASS | Git Bash syntax check |
| Production PHP error settings | PASS | Display/startup errors Off; logging/ignore exception args On |
| Local XAMPP Apache default configuration | PASS | `httpd.exe -t`: Syntax OK |
| New Apache access rules over HTTP | NOT TESTED | Isolated Apache config rejected its temporary config path locally |
| Docker build, container Apache, Linux ownership/modes | NOT TESTED | Docker unavailable; startup retains runtime www-data validation |
| PHP 8.3 runtime | NOT TESTED | Available runnable PHP is 8.2.12 |
| Render deployment, existing admin ID 1, Aiven connectivity/schema | NOT TESTED | No production logs/credentials; production URL inaccessible to browsing tool |

An intermediate test assertion assumed order ID 1; the forced rollback correctly
consumed an auto-increment value. The fixture now uses the actual committed ID.
This was a test assumption, not a production account/record change.

Run the isolated suite (Python 3.12+, PHP pdo_mysql/openssl, MariaDB, OpenSSL):

```powershell
python tests/integration.py --php C:/xampp/php/php.exe --mysqld C:/xampp/mysql/bin/mysqld.exe --openssl "C:/Program Files/Git/usr/bin/openssl.exe"
rg --files -g '*.php' | ForEach-Object { & C:\xampp\php\php.exe -l $_ }
& 'C:\Program Files\Git\bin\bash.exe' -n docker/start-pc-forge
git diff --check
```

The suite starts only its own loopback MariaDB server with a temporary data
directory and generated one-day certificate. Its fixture server uses disabled
grants only inside that isolated loopback instance; production PDO/TLS security
is unchanged. All inherited DB_* settings are replaced. Services stop and their
temporary data/certificates are deleted after the run.

## Deployment configuration

Required Render environment variables:

```ini
DB_HOST=<Aiven hostname>
DB_PORT=<Aiven MySQL port>
DB_NAME=pc_forge
DB_USER=<existing Aiven user>
DB_PASSWORD=<existing secret>
DB_SSL_CA=/run/pc-forge/ca.pem
```

`RENDER=true` is Render's platform-provided marker for trusting its forwarded
HTTPS protocol. Enforce HTTPS at the deployment edge. No credentials belong in
Git, the Dockerfile, logs, browser responses, or this document.

Keep the Render Secret File named `ca.pem`, mounted at `/etc/secrets/ca.pem`.
The existing startup fix remains: root copies it to `/run/pc-forge/ca.pem`, mode
640, ownership root:www-data; directory mode 755. It validates access/PEM as
www-data before `exec apache2-foreground`. TLS verification and native prepares
remain enabled. No environment variables were changed remotely.

Use the Dockerfile default command. Remove any Render Docker Command override
that bypasses `start-pc-forge`. PHP 8.3 Apache, PDO MySQL, document root, rewrite
and headers modules, and stderr error logging are retained. No application rewrite
router is needed: existing routes use PHP filenames. With Docker installed:

```powershell
docker build -t pc-forge:audit .
docker run --rm --entrypoint apache2ctl pc-forge:audit -t
```

The second command validates container Apache syntax without starting the app or
requiring database credentials. Full startup still requires the secret mount and
the environment above.

## Files changed

- `.dockerignore`, `.htaccess`, `Dockerfile`, `README.md`, `AUDIT.md`
- `bootstrap.php`, `config/db.php`, `config/orders.php`, `config/.htaccess`
- `login.php`, `register.php`, `logout.php`, `layout.php`
- `index.php`, `cart.php`, `checkout.php`, `orders.php`, `admin/index.php`
- `database/inspect.sql`, `database/.htaccess`, `docker/.htaccess`
- `tests/integration.py`, `tests/.htaccess`

The earlier certificate startup and production INI files were inspected and
preserved without weakening their settings. Existing storefront CSS/branding,
schema records, users, passwords, admin assignment, products, and orders are kept.

## Remaining limits and Render verification

There is no standalone product-detail route, category CRUD screen, customer CRUD
screen, upload system, or payment gateway in this repository. Existing categories
are selectable for products. COD and bank transfer are manual/demo bookkeeping;
marking a payment paid does not process a payment. Remote product-image delivery
depends on the image host. Rate limiting, password recovery, centralized session
storage for multiple instances, payment gateway integration, and load testing
remain separate production hardening work.

After reviewing/committing these changes, deploy using Render's normal process:

1. Verify environment names and runtime CA path above. Do not reset passwords or
   create another admin account. Leave the existing ID 1 role assignment intact.
2. Check startup logs for CA validation as www-data. A certificate/config failure
   must stop startup, not launch an insecure database connection.
3. Open the storefront, category/search and login pages. On HTTPS verify Secure,
   HttpOnly and SameSite cookies in browser developer tools.
4. Sign in with an existing admin account: confirm redirect to `/admin/index.php`.
   An existing customer must receive HTTP 403 for admin routes/actions. Anonymous
   access must redirect to login. Use POST logout from navigation.
5. If a page fails, inspect private Render logs for SQLSTATE/driver code, route,
   file and line. Compare read-only schema metadata if codes indicate missing
   columns/tables. Do not publish credentials/log dumps or rerun schema.sql.
6. Verify `/config/db.php`, `/database/schema.sql`, `/docker/production.ini`, and
   `/.git/config` are forbidden. Confirm CSS and existing UI still load.
7. Run write-based registration/checkout/admin smoke tests in staging with
   authorized disposable fixtures, not automatically against live production.

Commit and push only after review (not executed by this audit):

```powershell
git add .dockerignore .htaccess Dockerfile README.md AUDIT.md bootstrap.php config/db.php config/orders.php config/.htaccess login.php register.php logout.php layout.php index.php cart.php checkout.php orders.php admin/index.php database/inspect.sql database/.htaccess docker/.htaccess tests/integration.py tests/.htaccess
git commit -m "Repair authentication, error handling, checkout and deployment safeguards"
git push origin HEAD:main
```
