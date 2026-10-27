# Existing Render service: authorized synthetic XSS demonstration

## Scope and current status

### Persistent anonymous 403: startup diagnostics v3

200 on `/` and `/login.php` proves general availability, not that the optional
demo passed its startup gate. 401 is expected only when the enabled authenticated
policy is loaded **and** Apache sees X-Forwarded-Proto exactly equal to https.
The current source deliberately returns 403 in these cases:

| Diagnostic reason / layer | Meaning and corrective action |
| --- | --- |
| not-enabled | XSS_DEMO_ENABLED absent or not exactly 1; correct that existing-service setting |
| invalid-tester-name | Missing/invalid dedicated username; use the documented allowed characters |
| invalid-bcrypt | Missing/malformed hash, wrong cost or accidental username prefix/quotes; use only the literal bcrypt hash, cost 8–14 |
| invalid-expiry | Missing/non-digit value; use Unix seconds, not a date string |
| expired | Window already ended; generate a fresh approved short window |
| expiry-over-eight-hours | Future timestamp exceeds eight hours; milliseconds also commonly trigger this |
| runtime-file-preparation-failed stage=auth-directory/auth-file/apache-policy | Startup could not prepare the named runtime stage; use safe file/worker-read diagnostics, not broad permission grants |
| Apache config=NOT-LOADED | Apache include tree did not load the generated file; inspect IncludeOptional/vhost/startup overrides; startup now stops |
| Apache config=syntax-or-includes-failed | Apache parse/include command failed; startup now stops; run apache2ctl -t in the service shell for exact syntax details |
| Loaded tester-authentication, internal HTTPS request=401 but external=403 | Check the actual Render proxy/deploy path and competing vhost/Location policies; do not remove the HTTPS requirement |
| Request denied layer=php reason=expired, etc. | Request reached PHP after Apache authorization, then failed the independent runtime gate |

No single reason is confirmed for your deployed service without its diagnostic
output. A static expiry from an earlier exercise legitimately expires even while
the storefront keeps returning 200. Do not change the denial to Require all granted.

#### Inspect Render Logs and prove the deployed revision

1. Review/commit the diagnostic changes and obtain push/deploy approval. Nothing
   here pushes automatically. A local edited/untracked file is not part of any
   deployed commit. Record `git status --short` and `git rev-parse HEAD` after the
   intended changes are committed; confirm the remote commit contains the files.
2. In Render Dashboard select the existing PC Forge service. Open its deployment
   event/details and compare its commit SHA with that expected commit. Confirm
   the connected repository/branch and default Docker Command/startup settings.
   An override that launches apache2-foreground directly bypasses preparation and
   the diagnostic gate. Keep the Dockerfile CMD start-pc-forge.
3. Deploy/rebuild the reviewed commit only after approval. Redeploying an old image
   or using Save and deploy for settings alone does not add new source files.
   Save only leaves old runtime settings in effect until a deployment occurs.
4. Open service **Logs**, select the new deploy's startup time window/instance,
   and search for `PC Forge XSS`. The expected sequence is:

   ```text
   PC Forge XSS diagnostics revision=xss-startup-v3 commit=<40-character SHA>
   PC Forge XSS settings enabled=yes reason=enabled
   PC Forge XSS flags enable_exact_1=yes tester_name=valid bcrypt=valid expiry=valid
   PC Forge: XSS demo route authenticated reason=enabled target=/opt/pc-forge-xss
   PC Forge XSS Apache config=loaded
   PC Forge XSS loaded policy=tester-authentication alias=present
   ```

   Missing revision=xss-startup-v3 means the new startup code did not execute:
   distinguish old deployment, wrong instance/log window or startup override.
   commit=unavailable means that variable was unavailable/invalid, not permission
   to assume the local commit is deployed. Compare the Render deployment event.
   Check every running instance if the service has multiple instances.
5. In Render **Shell** on that deployment:

   ```sh
   php /usr/local/lib/pc-forge/diagnose-xss-demo.php
   php /usr/local/lib/pc-forge/verify-xss-apache.php
   apache2ctl -t
   apache2ctl -t -D DUMP_INCLUDES
   apache2ctl -S
   ```

   `verify-xss-apache.php` checks Apache's parsed include tree, not just whether
   a file exists. It logs only status and policy type, never raw command output
   or credentials. It runs automatically after policy generation and before the
   supervisor; missing/invalid/unrecognized policy prevents unchecked startup.
   The second startup parse does not change auth/expiry/sandbox rules. A shell
   check describes current files; pair it with the startup log of the running
   process to detect manual changes after startup.
6. If settings and include checks pass but anonymous external requests are still
   403, compare these **credential-free** internal requests from Render Shell:

   ```sh
   curl -s -o /dev/null -w 'forwarded-https: %{http_code}\n' -H 'Host: pc-forge-k68s.onrender.com' -H 'X-Forwarded-Proto: https' http://127.0.0.1/xss-demo/
   curl -s -o /dev/null -w 'without-forwarded-https: %{http_code}\n' -H 'Host: pc-forge-k68s.onrender.com' http://127.0.0.1/xss-demo/
   ```

   Enabled authenticated policy expects first=401, second=403. Both=403 points
   back to disabled/overriding authorization or a different active vhost; check
   the include/vhost dump. First=401 and external=403 narrows investigation to
   external routing/forwarding or a different instance; never weaken the check.
   Do not include Basic credentials in these diagnostic requests.
7. Correct only the named setting/runtime problem, obtain approval for any
   settings-triggered deployment, then repeat the existing HTTP verifier. Its
   expected progression is public 200, anonymous demo 401, authorized demo 200.
   Live browser/sandbox acceptance remains a separate required check.

Render documents [RENDER_GIT_COMMIT as the deployment SHA](https://render.com/docs/environment-variables),
and the different [environment save/deploy options](https://render.com/docs/configure-environment-variables).
Diagnostics log only that validated non-secret SHA, fixed reason codes and validity
flags. They never log tester names, passwords, bcrypt hashes, expiry values,
Authorization/Cookie headers, payloads, request bodies or database variables.

Added diagnostics helper and loaded-config verifier are packaged by Dockerfile.
The request PHP guard now logs only a fixed reason if it independently denies
access. Existing auth, expiry conditions and CSP/browser sandbox are unchanged.

Offline validation commands:

```powershell
python tests/test_xss_diagnostics.py --php C:/xampp/php/php.exe
python tests/test_xss_startup_policy.py --php C:/xampp/php/php.exe
python tests/xss_render_checks.py --php C:/xampp/php/php.exe
python tests/test_xss_apache_routing.py --php C:/xampp/php/php.exe
```

The real Apache regression additionally checks DUMP_INCLUDES output using the
actual parser and a temporary included fragment. No Render configuration or
credentials are needed; it does not prove which policy is deployed remotely.

Executed validation for diagnostics v3: secret-redaction/include-parser tests,
startup-policy tests, hosted-rendering checks, eight XSS tests, two ownership/CSRF
tests, PHP source checks and syntax checks on all 35 PHP files PASS. The real
XAMPP Apache fixture passes its old/enabled/disabled policy cases, generated
include-tree recognition, and anonymous missing-forwarded-HTTPS=403 versus
forwarded-HTTPS=401. Actual Render startup and browser execution remain untested.

### Apache 403 repair and precise diagnosis

Reported Render log: `AH01630: client denied by server configuration:
/var/www/html/xss-demo`. That is an Apache authorization denial, not proof of a
Unix file-mode failure. The enabled design maps `/xss-demo/` to
`/opt/pc-forge-xss/`, not a document-root directory. Creating/chmodding
`/var/www/html/xss-demo` is not the repair.

The exact original disabled policy generated by `docker/xss-demo-config.php` was:

```apache
<LocationMatch "^/xss-demo(?:/|$)">
    Require all denied
</LocationMatch>
```

In that mode the original generator emitted no Alias. That combination was
reproduced with real XAMPP Apache: authorized as well as anonymous requests are
403 and the error points at the document-root xss-demo path. Missing enablement,
invalid username/hash, invalid/expired expiry or a private-auth-file preparation
failure could all select this denial. The log alone does not establish which
condition selected it on Render. No live Render shell access was available here.
The root `.htaccess` does not match `/xss-demo/`; it blocks the distinct source
path `/xss-demo-src`. The enabled slashless `^/xss-demo$` denial does not match
the slash URL and its query string. Leave both source and slashless protections.

Correction: both enabled and disabled generated policies now declare the correct
Alias. Enabled mode explicitly sets `AuthMerging Off` for the destination Directory
and retains Require valid-user AND forwarded HTTPS; it never adds Require all
granted. Disabled mode still denies the namespace and target Directory. A pure
settings validator and startup reason messages make the selected mode observable
without logging usernames, password hashes, expiry values or credentials. Expiry
and sandbox controls in the PHP adapter are unchanged.

An Alias applies authorization at its destination Directory; see the official
[Apache Alias documentation](https://httpd.apache.org/docs/2.4/mod/mod_alias.html#alias).
AuthMerging Off explicitly replaces an inherited authorization policy with the
destination's authenticated policy; it does not bypass authentication. See
[Apache AuthMerging](https://httpd.apache.org/docs/2.4/mod/mod_authz_core.html#authmerging).

**The route will intentionally remain 403 if settings are disabled/invalid.** The
routing patch does not silently enable it. Correct the private Render settings
and redeploy in the approved testing window to generate the authenticated policy.

#### Exact deployment and live diagnosis steps

1. Before deployment, in Render Shell on the current service inspect the actual
   loaded policy (no htpasswd contents or environment dump):

   ```sh
   apache2ctl -t
   apache2ctl -S
   apache2ctl -t -D DUMP_INCLUDES
   grep -nE 'Alias|Directory|LocationMatch|Require|AuthMerging' /etc/apache2/conf-enabled/pc-forge-xss.conf
   ls -ld /var/www/html/xss-demo /opt/pc-forge-xss /run/pc-forge-xss-auth
   ```

   A missing `/var/www/html/xss-demo` is expected and is not a prerequisite. A broad
   LocationMatch denial with no Alias confirms the reproduced original disabled
   mode. If the loaded policy differs, retain that evidence; check VirtualHost
   overrides/duplicate LocationMatch policies before claiming the same root cause.
   This repository generates a global Alias/Directory fragment, not a new vhost.
2. Generate the tester hash and a fresh two-hour expiry using the commands below.
   Set XSS_DEMO_ENABLED=1, the dedicated username, the literal bcrypt hash and the
   future Unix seconds on this **existing service**. Do not use milliseconds or an
   expiry more than eight hours ahead. Saving settings may deploy; obtain approval
   before that action. Preserve DB/training settings and the default start command.
3. After push/deploy approval, deploy the reviewed commit containing this repair.
   No push/deploy is performed by these instructions or scripts automatically.
   Look for `PC Forge: XSS demo route authenticated reason=enabled
   target=/opt/pc-forge-xss` in startup logs. A `denied reason=...` log means
   the named setting must be corrected and the service restarted/redeployed.
4. In Render Shell run the packaged safe diagnostic and check actual read access:

   ```sh
   php /usr/local/lib/pc-forge/diagnose-xss-demo.php
   apache2ctl -t
   apache2ctl -S
   su -s /bin/sh www-data -c 'test -r /opt/pc-forge-xss/index.php && test -r /opt/pc-forge-xss/render.php && test -r /opt/pc-forge-xss/style.css && test -r /run/pc-forge-xss-auth/testers && echo "PASS: Apache worker can read demo and authentication files"'
   ```

   Expected: enabled reason=enabled; Alias present; tester authentication present;
   blanket disabled URL denial absent; generated settings match. The diagnostic
   reports existence, ownership and mode for both possible filesystem paths but
   never reads/display auth file contents. Target directory mode is 0750 and PHP/
   CSS files 0640, root:www-data; private auth directory/file are 0750/0640.
5. Run `python tests/verify_xss_render.py --verify-live --http-only` on Windows.
   Anonymous slash URLs must be 401, correct tester credentials 200, invalid
   payload 400, and public homepage/login 200. Do not send credentials over HTTP.
   Then run the full browser verifier documented below. Close tester tabs and
   disable/redeploy when the exercise is complete.

#### Routing regression results

`python tests/test_xss_apache_routing.py` exercised generated policies in a disposable
XAMPP Apache VirtualHost, with synthetic static adapter content and no production
PHP/database. PASS: old denial reproduced the document-root AH01630; all three
configurations passed Apache syntax; enabled anonymous/wrong-password = 401;
both valid-tester versions = 200 at the Alias destination; missing forwarded HTTPS
= 403; slashless route = 403; corrected disabled mode = 403 even with credentials;
public root = 200 in every mode. It does not test PHP expiration or browser JS.

The first sandboxed invocation could not read its temporary config (AH00532).
The approved rerun outside that filesystem sandbox passed; installed Apache
configuration was not edited. `tests/test_xss_startup_policy.py` passes enabled,
missing, malformed, expired and over-eight-hour settings. Hosted rendering, eight
XSS tests, two access-control/CSRF tests, syntax/source checks on all 33 PHP files, Python compilation and
whitespace checks also pass. These results do not establish the actual loaded
Render configuration or deployed browser result.

Files changed for this repair: Dockerfile, docker/xss-demo-config.php,
docker/prepare-xss-demo.php, tests/xss_render_checks.py and this guide.
Files added: docker/diagnose-xss-demo.php, tests/test_xss_apache_routing.py,
tests/test_xss_startup_policy.py. No production login, checkout, SQL, authentication
application logic, credentials, demo expiry gate or sandbox policy changed.

---

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
   with expired settings denies the route while retaining its Alias. Expiry does not erase an already-open
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
PASS: all 33 PHP syntax/source checks, Python compilation and whitespace review.

NOT RUN: actual generated Apache syntax/auth challenge in Linux/Render, live
HTTP verification, actual browser alerts/opaque-origin behavior, remaining business
workflow after the failed login test and deployed PHP 8.3. No private tester configuration or deployment
approval was supplied, and Playwright is not installed here. Keep the demo disabled
until these acceptance checks are performed in the approved deployment window.
