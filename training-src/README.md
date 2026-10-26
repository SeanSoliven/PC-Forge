# Single-service training infrastructure — safe preview only

Linux Docker verification is now automated by `.github/workflows/isolation.yml`.
You do not need Docker Desktop or WSL locally. See
[`docs/ci-isolation.md`](../docs/ci-isolation.md) for the jobs, synthetic fixtures,
how to view GitHub Actions results, and the remaining database verification gate.

## Status and mandatory blocker

Vulnerable authentication is **not implemented or enabled**. This is the explicit
fallback requested when reliable isolation cannot be verified. Docker and Linux
are unavailable in the development environment, and no independent training DB
credentials/grants were provided. Consequently Linux process/filesystem isolation,
container Apache/Linux isolation and DB privilege isolation have not been executed
here. Apache authentication/header filtering was verified using a disposable local
Windows Apache proxy fixture. Do not label this a working vulnerable deployment.

The existing public storefront stays at `/`. A disabled-by-default instructor-only
safe preview is available at `/training/` after explicit configuration. It reuses
the production CSS and storefront/login layout with hardcoded synthetic products.
It has no database, sessions, SQL injection, brute-force runner, registration,
checkout, orders, payments, or functional training login. POST login returns 503.
Cart/Register preview links lead to the unavailable login; no real operation runs.
This is visual scaffolding, not a fully functional copy of the store.

## Implemented architecture

- Same Render service, same hostname, Apache still listens on port 80. No second
  service is created. Production continues using PHP 8.3 Apache and PDO MySQL.
- Production source is root:www-data, directories 750/files 640. Source folders
  are denied over HTTP. Production sessions and login budgets use private runtime
  directories owned by www-data. The existing CA copy stays root:www-data mode
  640 at `/run/pc-forge/ca.pem`, with `/etc/secrets/ca.pem` unchanged.
- Preview source is copied outside the public root into `/opt/pc-forge-training`,
  root:pc-training mode 750/640. A dedicated non-login OS user runs an independent
  PHP CLI backend bound only to 127.0.0.1:9081. It starts through env -i both before and after runuser/PAM, without
  DB_*, Render, instructor credentials, or production PHP INI configuration.
- Before the preview starts, verify-training.php runs under the actual training
  UID, without open_basedir hiding OS-permission failures. It checks forbidden
  files/directories, inherited production variables, UID, and /proc/1/environ.
  Any failed probe stops startup rather than opening an unverified route.
- Backend open_basedir adds a second restriction; command/process execution and
  URL fopen are disabled. No arbitrary PHP path is routed. The router reads a protected per-startup proxy-token file (never a command-line or environment token), and rejects Cookie/Authorization headers outright.
- Apache authenticates instructors with a root-controlled bcrypt htpasswd file,
  requires forwarded HTTPS, strips all inbound cookies/authorization before
  proxying, and removes outgoing Set-Cookie headers from both response tables.
  The preview currently needs no browser session: no training cookie is issued.
  A private future session directory/name/path/Secure/HttpOnly/Strict settings are
  provisioned, but cookie forwarding remains disabled until verified explicitly.
- Apache and preview are supervised together; termination of either stops the
  container. Authentication configuration/proxy tokens are private runtime files,
  not committed secrets. The public navigation is unchanged.

These are implemented controls, not a container/sandbox-equivalence claim. Same-
container resource exhaustion, shared kernel/network, and same-origin browser
risks remain. A raw script-executing XSS demonstration would share production's
origin even with different cookie names; it is intentionally absent. CSRF bypass,
IDOR and broken-access-control exercises are also deferred until isolated data,
sessions, instructor scope, and expiration budgets can be verified.

## Production login throttling

Native prepares, password verification, CSRF and redirects are retained. Requests
with valid CSRF are budgeted before SQL/password verification: 15 per normalized
email in a fixed five-minute window. There is no aggregate IP budget. Limits survive
session changes. HTTP 429 includes Retry-After and a generic message; logs contain
no submitted credentials. Account identifiers are hashed in a locked, bounded
JSON store; expired entries are pruned. Storage failure fails closed with the
existing safe error handling. Successful logins consume requests too.

A shared Render/NAT proxy IP cannot pool unrelated users into one throttle budget:
IP addresses are no longer used as bucket keys. A 650-distinct-account regression
covers this. Per-account budgets can still be abused to temporarily deny a known
account, and corrupt storage, unavailable disk or a full 10,000-account window can
reject requests. Existing tracked accounts continue to use their budget when the
store reaches capacity; new accounts wait for expiry. This is not a guarantee of
unlimited availability. Budgets reset on redeploy/restart and are not distributed
across multiple Render instances. No schema migration is needed.

## Render configuration (manual, not changed here)

Leave these production settings unchanged:

```ini
DB_NAME=pc_forge
DB_SSL_CA=/run/pc-forge/ca.pem
```

Keep the original `ca.pem` secret at `/etc/secrets/ca.pem` and existing Aiven
DB_HOST/DB_PORT/DB_USER/DB_PASSWORD. The Dockerfile default command is required.
All production credentials remain private; no live database is touched by setup.

Training is disabled unless `TRAINING_PREVIEW_ENABLED=1`. To enable **only the safe
preview**, after running the container tests, manually supply:

```ini
TRAINING_PREVIEW_ENABLED=1
TRAINING_INSTRUCTOR_USER=<new instructor identifier, letters/digits/underscore/hyphen>
TRAINING_INSTRUCTOR_BCRYPT=<bcrypt hash, cost 4–14, unique instructor password>
```

Generate the bcrypt hash in a trusted local password tool or interactively using
`htpasswd -nB instructor` (enter the password at its prompt); store only the hash
portion after the colon in Render. Do not use a production account password.
Never commit the password/hash or supply a plaintext password as an environment
variable. Instructor browser authentication uses Basic over HTTPS; credentials
are stripped before the backend. It has no application logout and no instructor
rate limiter yet, so use a high-entropy password and do not enable without those
operational limitations being acceptable. Rotation requires replacing the hash
and redeploying normally. Preview auth logs remain in Apache's normal logs.

If the mounted original CA or production directories are readable by pc-training,
the startup probes deliberately reject preview startup. Do not bypass the probe.
Investigate mount permissions or keep preview disabled. No chmod of the original
Render secret is attempted automatically.

To disable completely, remove/set TRAINING_PREVIEW_ENABLED=0 and redeploy normally.
Apache then denies `/training` and its descendants, no preview process starts, and
no instructor credentials are required. There is no variable that enables SQL
injection; the code does not exist in this implementation.

## Separate synthetic database — manual preparation only

Provision a separate training MySQL instance/isolated database account, never
pc_forge or mens_daydb. `database/setup.sql` creates pc_forge_training and synthetic
users/products only. It fails if the database already exists; do not drop existing
data to bypass failures. Its plaintext demo_password column is teaching data only.
The synthetic passwords are lab-customer-123 and lab-admin-123. The runtime reader
must have SELECT on only users/products, no roles, global/schema-wide privileges,
FILE, PROCESS, EXECUTE, DDL/DML or admin privileges. Require TLS and an independent
CA/configuration. SHOW GRANTS and real denied-access tests must be performed before
a backend can use it. The safe preview has no DB configuration and ignores any
TRAINING_DB_* variables; do not add production credentials to them.

`database/reset.sql` resets only the known synthetic rows and stock when run by
the separate training owner. Every write in setup/reset is schema-qualified, even if a client ignores errors.
It never drops tables or resets production users.
It does not recreate deleted rows. No web reset endpoint exists yet; owner-only
manual reset avoids giving the future SQL-injectable reader write permissions.

A future vulnerable backend requires explicit new code after verification: TLS
PDO with native prepares for secure comparison, read-only credentials and disabled
multi-statements for the intentionally injectable query, separate durable audit
and budget storage, an instructor-bound expiring window, and a hard attempt cap.
Use only synthetic accounts, record outcomes without passwords, and distinguish
real credential success from bypass. Do not test payloads on real production
accounts. SQL injection, bounded brute-force, and extra exercises are **deferred**.

## Tests and deployment gates

Local commands:

```powershell
php tests/training_checks.php
python tests/training_http.py --php C:/xampp/php/php.exe
python tests/apache_training.py --php C:/xampp/php/php.exe
python tests/integration.py --php C:/xampp/php/php.exe --mysqld C:/xampp/mysql/bin/mysqld.exe --openssl "C:/Program Files/Git/usr/bin/openssl.exe"
python tests/php_source.py
```

Linux/Docker gate, not executed locally:

```sh
bash tests/container-isolation.sh
```

Run it from a Linux filesystem with Docker Engine available (`docker version`),
curl, OpenSSL and Bash. It builds the image itself and uses only disposable
containers and synthetic fixtures; no production environment file is required.
Docker Desktop/Windows bind-mount permissions can differ from Linux/Render, so
use Linux filesystem mounts for this gate. A successful preview gate is not
authorization to enable vulnerable authentication or proof of real DB grants.

It builds the image, uses a generated temporary CA and synthetic production-secret
marker, tests default denial, instructor gate, forwarded-cookie/auth stripping,
blocked preview login, live worker UIDs, actual production secret/session-file
denials, forged training-session rejection by production, CA permissions,
supervisor shutdown, malformed startup configuration, and Apache syntax.
The credential-independence check uses synthetic markers only: it does NOT verify
real DB grants. Real training credentials/TLS/denied-access checks remain mandatory.
No Aiven credentials or existing database server is used. Also test real mount
permissions, Render-specific restart behavior, HTTPS proxy behavior, unauthenticated static
requests, public storefront/login, and protected admin routes in staging. Confirm
no leaked Set-Cookie or instructor credentials at the boundary. A full kernel or
arbitrary-code sandbox is not established by these checks.

Apache header removal uses its documented late request processing, after normal
authentication and before the content handler:
https://httpd.apache.org/docs/2.4/mod/mod_headers.html
Reverse-proxy configuration reference:
https://httpd.apache.org/docs/2.4/mod/mod_proxy.html

No automatic push, deployment, Render configuration, or live DB grant change is
performed. See TEST_RESULTS.md for executed results and exact changed-file list.
