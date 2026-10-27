# PC Forge: clickjacking, access control and CSRF readiness

Assessment date: 2026-10-28 (Asia/Manila).
Target: `https://pc-forge-k68s.onrender.com`.
Method: current repository inspection and PHP CLI regressions. No live target
requests, production changes, pushes or deployments were performed.

## Recommendation and classification

**Clickjacking is the best candidate for a practical before/after exercise**, subject
to live confirmation. No storefront framing policy was found in the inspected
source. A harmless embedding demonstration can establish frameability; a later
approved header fix can block the same frame. Frameability alone does not prove
a sensitive action can be induced, and an absent header alone does not establish
browser behavior. Never click or disguise a sensitive control for this exercise.

| Attack | Classification | Actual evidence currently available |
| --- | --- | --- |
| Clickjacking | Potential vulnerability requiring live verification | Storefront lacks X-Frame-Options and CSP frame-ancestors in inspected source; deployed edge headers/browser result not tested |
| Broken access control / IDOR | Protected in inspected routes | Session-bound order query, admin role gate before actions; CLI order-template test passed for two synthetic identities |
| CSRF | Protected in inspected routes | Random session token, string validation, constant-time comparison and checks before business mutations; real-helper negative cases passed |
| Deployed authorization / CSRF behavior | Not tested | Requires controlled accounts and manual live checks below |
| Confirmed vulnerabilities | None | No live exploit claimed |

“Protected” here describes reviewed controls and offline evidence, not an exhaustive
guarantee for every deployed request, database state or future endpoint.

## 1. Clickjacking

**Files inspected:** `.htaccess`, `bootstrap.php`, `Dockerfile` generated Apache
configuration, `docker/start-pc-forge`, `docker/production.ini`,
`docker/training-config.php`, `docker/training-router.php`, `layout.php` and the
production PHP entry points. No production X-Frame-Options or frame-ancestors
directive was found. The instructor-only training route has `frame-ancestors
'none'`; it does not protect the storefront. No client-side frame-busting script
was found. nosniff, Referrer-Policy, no-store and HttpOnly/SameSite cookies are
present but are not replacements for a framing policy.

Potentially frameable HTML routes from source: `/`, `/index.php`, `/login.php`,
`/register.php`, `/cart.php`, `/checkout.php`, `/orders.php`, `/admin/index.php`.
Authentication/redirects still govern protected pages. These are candidate URLs,
not a claim that each embeds successfully. Only test the anonymous login page
for the harmless framing baseline; do not frame an authenticated admin page.

**Safe reproduction:** record actual deployed commit, UTC timestamp and browser
version. In DevTools Network inspect GET `/login.php` for response
X-Frame-Options and Content-Security-Policy. Check the final HTML response after
any redirect, not just an intermediate response or a meta tag. A Report-Only
policy does not enforce framing restrictions.

Save this fixed HTML outside the repository as `pcforge-frame-check.html` and
open it directly in the browser. No local server, Docker or WSL is involved.
It makes one embedded GET to the actual target; do this only in an anonymous
browser profile with no production login cookies. Do not interact with the form.

```html
<!doctype html>
<html lang="en"><meta charset="utf-8">
<title>PC Forge framing check</title>
<h1>Visible, read-only framing check</h1>
<p>Do not enter credentials or click inside the frame.</p>
<iframe title="Anonymous PC Forge login framing test"
  src="https://pc-forge-k68s.onrender.com/login.php"
  sandbox="" referrerpolicy="no-referrer" width="1000" height="650"></iframe>
</html>
```

The sandbox disables form submission and scripts, and intentionally provides no
allow-same-origin permission. It is not an overlay, credential collector or active
attack. Parent file origin and sandbox conditions must be recorded. Some browser
policies can make file-origin tests inconclusive. If needed, a future authorized
test on a separately controlled HTTPS origin can corroborate cross-origin behavior;
do not publish or deploy an embedding page automatically.

**Expected versus actual:** secure framing policy should block embedding and
produce an attributable browser console message. Current source predicts no
application-level block; actual Render behavior is **not tested**. A blank frame
alone is inconclusive (network/browser failures also cause it). Successful
anonymous embedding confirms frameability, not authenticated action exploitation;
SameSite/third-party-cookie behavior can affect authenticated scenarios.

**Evidence:** minimal header screenshot, visible frame or attributable console
refusal, parent origin, browser, timestamp and deployed commit. Exclude credentials,
cookie values, CSRF tokens and customer records.

**Recommended fix if confirmed:** add a consistent response-header policy through
Apache or the shared bootstrap, e.g. CSP `frame-ancestors 'none'` plus
`X-Frame-Options: DENY` where no embedding is required. Use `'self'` / SAMEORIGIN
only if legitimate same-origin embedding is needed. frame-ancestors must be an
HTTP response directive, not meta CSP. Review existing CSP before adding another
header and ensure error responses/HTML routes receive the intended policy.
No fix is implemented in this phase.

**Retest:** after approval and deployment repeat the identical parent file/browser
test and header inspection. Before = attributable embedding success; after =
attributable framing refusal. Preserve page design and ordinary top-level access.

## 2. Broken access control / IDOR

**Files/controls:** `orders.php` calls require_login and binds
`WHERE o.user_id=?` to `current_user()['id']`. No order-detail-by-ID endpoint was
found. Query parameters `id` and `user_id` are not used to select orders.
`placed` is an integer-cast notification only: changing it changes notice text,
not record access. This is not evidence of IDOR.

`admin/index.php` calls require_admin before rendering/dispatch; that helper in
`bootstrap.php` reads the current account's role from the database on each request.
Its order/payment/product IDs are actionable only after the admin gate and CSRF
check. Admins intentionally have cross-customer authority. `config/orders.php`
is an internal transaction helper, not a customer order controller: it does not
perform authorization itself, so every future caller must retain that boundary.
`checkout.php` takes user_id from the authenticated session, not a submitted field.
Cart contents live in the current session. `config/db.php`, helper routes and
logout were also reviewed; no additional object-read controller was identified.

**Safe reproduction:** use two already-existing controlled customer accounts A/B
in separate browser profiles and only known synthetic records belonging to them.
If no such records exist, mark record-isolation verification **Not tested**; do
not make purchases or enumerate IDs to create evidence. Empty order lists do not
prove cross-account isolation.

| Method/URL | Identity | Expected response / observation |
| --- | --- | --- |
| GET `/orders.php` | Anonymous | 302 Location login.php |
| GET `/admin/index.php` | Anonymous | 302 Location ../login.php |
| GET `/orders.php` | A, then B | 200; each sees only its own known synthetic orders |
| GET `/orders.php?id=B_ORDER&user_id=B_USER` | A | Same A-only order data; IDs ignored, not an expected 403 |
| GET `/orders.php?id=A_ORDER&user_id=A_USER` | B | Same B-only order data |
| GET `/admin/index.php` | A and B | 403 Admin access required |

Use actual known test-record IDs in place of the uppercase placeholders. Do not
test guessed IDs, POST admin mutations or log in as an admin to browse other
customers. If unexpected third-party content appears, stop, do not enumerate,
and record only the failure category without copying the content.

**Actual:** source and CLI fixture verify session-ID binding for two synthetic
identities despite supplied IDs; live A/B results **Not tested**. No missing
authorization check was confirmed in the reviewed reachable actions.

**Evidence:** redacted status/redirects, test-account labels A/B, only synthetic
order markers, baseline versus changed-query comparison and deployed commit.
**Recommended fix if failure confirmed:** enforce ownership in the selecting query
or authorized service layer; never trust client user_id; deny by default. Preserve
server-side admin role checks. Do not “fix” ignored query IDs into a new lookup.
**Retest:** repeat the same controlled A/B matrix after any approved fix; also
verify legitimate own-account access and admin authorization regressions.

## 3. CSRF

**Files/controls:** `config/db.php::csrf()` generates 32 random bytes, and
check_csrf rejects missing/non-string/mismatching tokens with hash_equals.
`login.php`, `register.php`, `cart.php`, `checkout.php`, `logout.php` and
`admin/index.php` validate before their business mutations. Forms carry hidden
tokens; layout navigation/logout and storefront/cart forms were inspected.
Checkout also has a separate checkout token. Logout requires POST (GET = 405).
SameSite=Lax is additional protection, not the primary verification. Cart and
registration are intentionally usable anonymously; anonymous does not mean CSRF
exempt. No endpoint accepting a tokenless business mutation was confirmed.

**Safe procedure:** in the browser's own-origin request editor/DevTools, use only
the dedicated account session. Replay at most one missing-token and one fixed
invalid-token request per selected endpoint, sequentially, at least two seconds
apart. Do not send a correct token with a mutation. Keep credentials and CSRF
values out of screenshots/terminal history. Observe response **message as well
as status**: field-validation failure alone is not proof that CSRF ran.

| Method/URL | Harmless negative payload (csrf omitted, then csrf=invalid) | Expected source behavior |
| --- | --- | --- |
| POST `/login.php` | Empty email/password | 422 form-expired message; no login attempt |
| POST `/register.php` | Empty name/email/password | 422 form-expired message; no account created |
| POST `/cart.php` | action=invalid-test-action | 422 form-expired message; cart unchanged |
| POST `/logout.php` | No other fields | 403 invalid-request-token message; session remains logged in |
| GET `/logout.php` | None | 405 with Allow: POST; session remains logged in |
| POST `/checkout.php` | Empty fields / invalid checkout_token | With empty cart: redirect to cart before CSRF, **inconclusive**. With pre-existing dedicated synthetic cart: 422 form-expired message; no order |
| POST `/admin/index.php` | No live admin request in this procedure | Customer = 403 authorization gate, **not proof of admin CSRF**; authenticated admin CSRF live test deferred |

For checkout do not populate a real checkout just for this test; defer if the
required controlled cart state is absent. No purchase is submitted. The deliberately
invalid business fields on other requests also limit impact if a token control
were broken. Missing-token logout could succeed if vulnerable: use only a
disposable dedicated session and stop after that result. Status 200/redirects
must be assessed in context, not automatically labeled CSRF bypass.

Do not browse admin order listings to test CSRF on a live data-bearing admin
session. Admin CSRF remains source-reviewed / live **Not tested** until a safe
dedicated-data setup and explicit procedure are available. Negative token replay
verifies server validation; it does not by itself demonstrate a successful
cross-origin exploit or cookie inclusion under all browser policies.

**Actual:** the real helper rejects missing, invalid, array and another-session
tokens and accepts the matching session token in CLI tests. All reviewed action
dispatchers call it. Live endpoint messages, mutation absence and authenticated
admin behavior have not been tested in this run.

**Evidence:** endpoint/method, account label, omitted/invalid token label, expected
token-error message, status and unchanged controlled session/cart state. Never
publish token or cookie values. **Recommended fix if a failure is confirmed:**
validate a session-bound unpredictable token before state change; reject unsafe
methods; retain SameSite and optional Origin checks as additional defenses.
**Retest:** repeat negative cases and, in an authorized safe fixture only, verify
valid requests still work. Never disable CSRF to manufacture a demonstration.

## Validation performed

```powershell
python tests/web_security_checks.py --php C:/xampp/php/php.exe
python tests/php_source.py
```

- Two new offline CLI tests PASS: actual CSRF helper negative/positive cases and
  actual order-template session ownership binding for two synthetic identities.
- All 24 repository PHP files passed syntax checks with XAMPP PHP 8.2.12;
  source/BOM checks PASS. PHP 8.3/Render runtime not verified here.
- Existing `tests/integration.py` includes customer admin denial, order-owner
  filtering, cart CSRF, logout CSRF and GET-method checks. It was inspected but
  not run in this no-localhost assessment; it starts a local fixture server.
- No local server, Docker, WSL or separate laboratory was used. New CLI fixtures
  substitute database/bootstrap boundaries, not a live MySQL authorization test.

Production code is unchanged. Record live status as **Not tested** until actual
evidence is collected. If Render already blocks frames, report clickjacking as
protected and select another **confirmed** finding rather than introducing one.
