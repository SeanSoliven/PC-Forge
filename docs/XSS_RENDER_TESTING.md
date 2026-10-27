# Existing Render service: authorized synthetic XSS demonstration

## Scope and current status

Deployment changes are prepared, **not pushed or deployed**. No live checks were
sent to Render. Apache/Linux startup, PHP 8.3 and actual sandboxed browser alerts
remain unverified in this environment. The target stays the existing
`https://pc-forge-k68s.onrender.com` service; no additional service is created.
No local Docker or WSL is required.

This is an intentionally vulnerable teaching adapter accepting **two fixed alert
payloads**, not an arbitrary public XSS endpoint or a discovered storefront exploit.
The production search, security helpers, accounts, database credentials and
SQL/brute-force implementations are unchanged.

## Why the earlier pages do not run on Render

`tests/` is excluded by `.dockerignore`, denied by `.htaccess`, and its demo support
requires CLI-server, loopback, an opt-in environment flag and the local router.
Apache on Render cannot satisfy those local guards. These restrictions remain.
Do not remove the tests exclusion or copy the local unrestricted renderer into
the document root.

Instead, the Dockerfile packages only the new `xss-demo-src` adapter and existing
CSS under `/opt/pc-forge-xss`, outside `/var/www/html`. Startup generates an
Apache Alias and Basic-auth policy. The raw source path `/xss-demo-src` is explicitly
denied in `.htaccess` because the repository COPY also includes it in document root.

## Controls and changed files

- `Dockerfile`: copies hosted adapter/CSS and root-only startup helpers.
- `docker/start-pc-forge`: prepares optional demo policy before the existing supervisor.
- `docker/xss-demo-config.php`: disabled-route denial or authenticated Directory/Alias.
- `docker/prepare-xss-demo.php`: validates settings and writes private htpasswd/config
  files, root-owned and mode 0640. Invalid/expired settings disable the demo; inability
  to write a denial policy stops startup rather than leave a stale enabled route.
- `xss-demo-src/index.php`: Apache-only entry, authenticated-user presence, forwarded
  HTTPS, explicit enablement, expiration and GET-only checks. No sessions/DB imports.
- `xss-demo-src/render.php`: exact synthetic-input allowlist, vulnerable/fixed renderers
  and narrowly scoped CSP. A request to this helper directly produces no demonstration.
- `.htaccess`: denies raw hosted source; existing production settings remain intact.
- `tests/xss_render_checks.py`: offline policy and rendering tests.
- `tests/verify_xss_render.py`: opt-in remote HTTP/browser verification; never deploys.

Both hosted versions require Apache valid-user authentication over forwarded HTTPS.
Production cookies are stripped at this route and outgoing Set-Cookie removed.
The renderer never reads accounts, customer data, credentials or session files.
It still runs in the existing Apache PHP process: this is not a separate OS/container
sandbox or a claim that production environment variables are inaccessible to PHP.
The fixed code and exact input allowlist prevent arbitrary PHP/JavaScript execution.

The demo CSP applies **only to its responses**. It creates an opaque browser origin
using `sandbox allow-scripts allow-modals`, without allow-same-origin, and blocks
network connections, frames, images, objects and form submissions. Only the
vulnerable version permits inline script. No production CSP is weakened. Inline
CSS is limited to this demo because opaque-origin rendering must not depend on
credentialed stylesheet fetches. A browser must verify sandbox/modal compatibility
before the demonstration is considered operational; never add allow-same-origin
or remove sandbox to work around a failed alert.
The [HTML dialog rules](https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html#simple-dialogs)
also allow browsers to suppress dialogs; the actual target browser must therefore
pass the verification, rather than inferring execution from response markup.

## Render variables — manual configuration only

| Variable | Value / requirement |
| --- | --- |
| `XSS_DEMO_ENABLED` | Default absent/0. Set 1 only for the approved exercise window |
| `XSS_DEMO_TESTER_USER` | Dedicated Basic-auth tester name, 1–64 letters/digits/underscore/hyphen |
| `XSS_DEMO_TESTER_BCRYPT` | bcrypt hash, cost 8–14, of a unique high-entropy disposable tester password |
| `XSS_DEMO_EXPIRES_AT` | Future Unix timestamp in seconds, at most eight hours from service startup |

No plaintext password environment variable is used. Supply the dedicated password
only to authorized classmates through your normal private channel; never use a
production account password. This implementation provides one configured tester
identity, not individual classmate accounts. Basic auth has no application logout
or new rate limiter; close the browser profile afterward and rotate/remove its
hash when finished. Do not reuse any training or production identity.

Generate a hash with XAMPP's password-prompt tool (no password command argument):

```powershell
& C:/xampp/apache/bin/htpasswd.exe -nB -C 10 xss_tester
# Copy only the hash after "xss_tester:" into XSS_DEMO_TESTER_BCRYPT privately.
[DateTimeOffset]::UtcNow.AddHours(2).ToUnixTimeSeconds()
# Copy this timestamp into XSS_DEMO_EXPIRES_AT shortly before the approved deploy.
```

Keep `DB_*`, Aiven CA settings, production credentials and training configuration
unchanged. Keep the existing Dockerfile default startup command. The demonstration
does not require enabling TRAINING_PREVIEW_ENABLED or PCFORGE_XSS_DEMO_ENABLED.

## Approved deployment sequence

**Current deployment blocker:** the full existing regression suite was run and
failed at `tests/integration.py:168` (incorrect password expected to be rejected).
The current pre-existing `login.php:39–44` checks user existence/role but omits
password_verify; its query is also directly concatenated. Neither behavior was
introduced or modified by this change. Do not deploy this checkout until the
responsible authentication/SQL workstream resolves that issue and the regression
passes. A synthetic fixture failure is not evidence of the deployed Render commit.

1. Review this diff and existing Render auto-deploy settings. Obtain approval
   **before pushing or deploying**, including saving variables that trigger redeploy.
2. After approval, deploy the code with XSS_DEMO_ENABLED absent/0 first. Confirm
   normal storefront availability and `/xss-demo/` denial (403). In Render Shell,
   `apache2ctl -t` should report Syntax OK. No live auth tests should run yet.
3. Prepare the dedicated tester hash and a short future expiry. After the agreed
   enablement approval, configure the four variables on the existing service and
   redeploy. No migration or grant change is involved.
4. Confirm Syntax OK and that unauthenticated requests are 401, authenticated
   requests are 200, the arbitrary-input test is 400 and browser sandbox isolation
   works. Do not share the exercise with classmates before this acceptance gate.
5. Run the browser verifier below. If it fails, disable the route and investigate;
   do not relax source allowlists, sandbox or production protections.
6. After evidence capture set XSS_DEMO_ENABLED=0, remove tester settings and redeploy
   after approval. Expiry also denies new requests immediately; a later restart
   with expired settings disables the Alias. Expiry does not erase an already-open
   page, so close tester tabs. Confirm route denial and ordinary storefront access.

## Hosted URLs and demonstration steps

- Fixed: `https://pc-forge-k68s.onrender.com/xss-demo/?version=fixed`
- Vulnerable: `https://pc-forge-k68s.onrender.com/xss-demo/?version=vulnerable`

Both are server-authenticated before content is served. The page provides links
for Normal, Reflected, Attribute and Bold inputs for both versions; no arbitrary
input-submission form is enabled. The search-looking input exists for the
attribute click proof. Exact `q` values accepted: empty, Synthetic, Ryzen,
`<b>XSS Test</b>` and these two fixed payloads:

```html
<script>alert('XSS Demonstration Successful')</script>
```

```text
" onclick="alert('XSS Demonstration Successful')" data-demo="
```

Authenticate using only the dedicated HTTP Basic identity, not the storefront
login. In the vulnerable page choose Reflected: expected alert on navigation.
Choose Attribute and click the search input: expected same alert. Repeat the exact
cases in Fixed: expected literal payload and no alert, no script/event-handler
node. An unexpected payload is rejected, not executed. Never use cookies, credential
capture, external requests or real-account data in a proof of concept.

Record deployed commit, UTC time and browser/version. Screenshots: unauthenticated
401; vulnerable alert and URL; attribute handler in Elements; fixed literal text and
encoded response; sandbox policy; unchanged ordinary storefront. Redact Basic
Authorization, cookies and all credentials. Label this an intentional synthetic
exercise, not a newly discovered vulnerability in production search.

## Verification commands

Offline checks (no Render traffic):

```powershell
python tests/xss_render_checks.py --php C:/xampp/php/php.exe
python tests/test_xss_demo.py --php C:/xampp/php/php.exe
python tests/xss_checks.py --php C:/xampp/php/php.exe
python tests/web_security_checks.py --php C:/xampp/php/php.exe
```

After approved deployment and enablement, HTTP-only verification:

```powershell
python tests/verify_xss_render.py --verify-live --http-only
```

This prompts privately for tester credentials, checks both anonymous/authorized
versions, cookie absence, sandbox policy, invalid payload denial and public `/`
and `/login.php` before/after. Credentials never become CLI arguments or saved
files. Requests are sequential with two-second pauses, certificate validation,
no inherited proxy and no automatic redirects. There are no retries, guessed
passwords, database operations or purchase mutations.

Full browser verification, when Python Playwright and its Chromium are available:

```powershell
python tests/verify_xss_render.py --verify-live
```

If needed, install this browser-test dependency on the tester's Windows machine:

```powershell
python -m pip install playwright
python -m playwright install chromium
```

The full check confirms the alert text in both vulnerable cases, no alert in
both fixed cases, and SecurityError on sandboxed localStorage access. Only demo
browser destinations are allowed. Browser cookies/storage are temporary and no
production account login is used. Verification prints statuses and a redacted
summary, not bodies, Authorization values or credentials.

Public homepage/login smoke checks do **not** prove the full business workflow.
Before releasing the change, run the existing regression suite in its disposable
fixture environment (not against live Aiven), and verify normal dedicated-customer
login/logout and UI manually without purchases. This phase does not alter or run
the separate SQL/brute-force assessment. No live script may report full success
without actual browser verification; --http-only is explicitly partial.

## Executed results and remaining gates

PASS: exact hosted payload allowlist and arbitrary-input rejection, disabled-default
Apache policy generation, auth/cookie directive presence, vulnerable/fixed response
rendering and non-Apache entry denial. PASS: existing local demo HTTP/isolation
suite, eight XSS regression tests, two CSRF/ownership CLI tests, new PHP syntax and
Python compilation. No Docker or WSL was invoked.

FAILED: existing full synthetic TLS/MariaDB regression stops at incorrect-password
rejection; current unchanged login lacks password verification (see blocker above).
PASS: all 32 PHP syntax/source checks, Python compilation and whitespace review.

NOT RUN: actual generated Apache syntax/auth challenge in Linux/Render, live
HTTP verification, actual browser alerts/opaque-origin behavior, remaining business
workflow after the failed login test and deployed PHP 8.3. No private tester configuration or deployment
approval was supplied, and Playwright is not installed here. Keep the demo disabled
until these acceptance checks are performed in the approved deployment window.
