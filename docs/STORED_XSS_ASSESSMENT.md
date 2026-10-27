# PC Forge stored-XSS assessment

Date: 2026-10-28 (Asia/Manila). Target: `https://pc-forge-k68s.onrender.com`.
Evidence: current repository trace and offline actual-template tests. No hosted
account was created and no production content was stored during this assessment.
The deployed commit and live stored-data behavior remain unverified.

## Answer: can registration Name support a real stored test?

**Yes, as a stored-input encoding test; no existing stored XSS is confirmed.**
`<b>XSS Test</b>` satisfies registration Name validation, is passed unchanged to
the parameterized insert for `users.name`, is loaded on login into the session,
and appears in the checkout Full name input through `e()`. This is an HTML marker,
not CSS and not a JavaScript payload. Accepting/storing its bytes does not make
the application vulnerable when each output context is correctly encoded.

Checkout uses a quoted attribute, not an HTML text node. Even an unescaped `<b>`
inside a quoted value would not automatically create bold text; a quote-boundary
test is necessary to check attribute containment. The tested encoded output
preserves both the basic marker and the fixed harmless quote-boundary marker.

## Input → storage → display inventory

Line references describe the current checkout; some templates occupy one long line.

| Candidate / source | Storage and later read | Output page / source lines | Expected and actual result |
| --- | --- | --- | --- |
| Registration Name: `register.php:8`, validation `:11` | INSERT `users.name`, `register.php:14–15`; login selects name `login.php:32–35`, session assignment `:52` | `checkout.php:1`, `value="<?=e(current_user()['name'])?>"` | Literal input value expected; actual registration insert-boundary and checkout fixture tests PASS; live pending |
| Registration email: `register.php:9` | `users.email`; normalized/validated; read by login and admin orders query | `admin/index.php:1`, `e($o['email'])` | Encoded text expected; source reviewed, no live admin browsing or stored-email test |
| Password / login inputs: `register.php:10`, `login.php:12–13` | Password hashed, not redisplayed; login email used for lookup, not reflected into form | `login.php:74–90`, blank fields and encoded generic errors | No user-text HTML sink identified here; no password exposure test performed |
| Profile fields | No profile edit/view route found | Only session name prefills checkout | No profile-specific attack route to reproduce |
| Search `q`: `index.php:1` | Not stored; used in prepared search | `index.php:3`, `value="<?=e($q)?>"` | Reflected marker stays literal; actual-template fixture PASS |
| Admin product name: `admin/index.php:1` | `products.name`; copied into `order_items.product_name` during checkout | `index.php:3` heading/alt, `cart.php:1`, admin inventory, all `e()` | Listing synthetic product fixture PASS; cart/admin source reviewed; live storage test not run |
| Admin product description / slug | `products.description` / `slug`; description searched | No description or slug output sink found in current pages | No current display path for stored HTML demonstration |
| Category name | `categories.name`; current admin UI selects category, does not create names | `index.php:3`, admin select, both `e()` | Synthetic listing/category fixture PASS; live pending |
| Admin image URL | `products.image_url`; admin validates HTTP/HTTPS, URL and length | `index.php:3`, quoted img src through `e()` | Synthetic quote-containing URL does not create attributes; fixture PASS; no external URL was fetched |
| Checkout full name / phone / address | `orders.shipping_name`, `shipping_phone`, `shipping_address`; checkout POST in `checkout.php:1` | No shipping field output found in `orders.php` or admin order list | Stored-XSS sink not identified; do not place an order to probe unseen output |
| Order statuses/payment/date | Restricted mutations / database generated timestamp | `orders.php:1`, escaped text; admin fixed options | Source reviewed; no arbitrary user-controlled option HTML identified |
| Numeric IDs / placed notification / quantities | Typed DB IDs and session cart quantities; placed cast to integer | Orders/cart/admin templates | No arbitrary HTML sink established from numeric outputs |
| Form errors | Application-generated validation messages | login/register/cart/checkout/admin use `e($error)` | No raw error sink found; unexpected exceptions use generic errors |
| Layout title / navigation | Title passed by PHP, role controls links | `layout.php:1`, `e($title)` | No profile name, arbitrary URL or client-input DOM sink found |

`config/db.php:97–102` defines `e()` with htmlspecialchars, ENT_QUOTES and UTF-8.
`bootstrap.php:50–55` handles scalar input/current session user. `database/schema.sql`
lines 3, 5, 8 and 9 define the relevant user/product/order storage columns.
`config/orders.php`, logout, Apache/configuration files, CSS and the training
preview were also reviewed for related paths. No application JS files, inline
scripts, innerHTML, outerHTML or document.write sinks were found. Test/document
strings mentioning these APIs are not production browser code.

The current login source concatenates its email into SQL. This belongs to the
separate SQL-injection workstream, is not an XSS finding, and was not changed or
tested here. Do not interpret this XSS review as a clean SQL/security assessment.

## Classification

| Finding | Classification |
| --- | --- |
| Registration name becomes markup in checkout | Not confirmed: offline actual output remains encoded |
| Product/category markup becomes HTML in listing | Not confirmed: synthetic output fixtures remain encoded |
| Search reflected XSS | Not confirmed: encoding fixtures pass |
| DOM-based XSS | No matching application sink identified in source |
| Missing production CSP | Source-confirmed defense-in-depth gap, not proof of XSS; Render headers unverified |
| Fixed unsafe versus encoded comparison | Simulation only, never a production exploit |

Missing CSP does not cancel correct encoding. HTML escaping is appropriate for
ordinary HTML text and quoted attributes; it does not replace URL scheme policy,
JavaScript encoding or HTML sanitization. No JS/CSS interpolation context was
identified in current templates. There is no reason to remove escaping to create
an exploit for the presentation.

## Safe hosted reproduction: dedicated registration Name

1. Record actual Render deployed commit, UTC time and browser version. Use a new
   dedicated customer identity you control, with no real customer information.
2. On `/register.php`, enter Name `<b>XSS Test</b>`, an unused controlled email
   and a disposable unique password. Submit once with the form's normal CSRF token.
   This creates a real dedicated account; do not create repeated accounts.
3. Sign in normally on `/login.php`. A fresh login is important: the checkout
   prefill comes from the session copy loaded at login, not a fresh name lookup.
4. Add one available item to this account's session cart, then open `/checkout.php`.
   Adding a cart item does not place an order or decrement stock in current source.
   If no suitable authorized item exists, defer this step instead of creating one.
5. **Do not submit checkout.** Observe the Full name value, raw Network response
   and DevTools Elements. Expected source: `value="&lt;b&gt;XSS Test&lt;/b&gt;"`.
   DOM input.value normally decodes to literal `<b>XSS Test</b>`; that is safe
   entity decoding, not a newly inserted b element or script execution.
6. Capture only the synthetic name/input and minimal escaped response fragment.
   Log out and remove the dedicated cart item when finished. Account cleanup is
   a separate owner-approved administrative action; this workflow deletes nothing.

If the hosted page unexpectedly creates markup, stop and document just the
synthetic fragment. HTML injection is distinct from confirmed JavaScript execution.
Do not escalate to event handlers, scripts, cookie reads, external requests or
other-user content. Actual hosted result is currently **Not tested**; do not fill
it with the offline fixture outcome. No dedicated account credentials were supplied
to this session, so an authenticated live result cannot be claimed.

Product-name storage would require an admin write visible to public customers;
do not create/edit public products just to run this assessment. The fixture tests
cover synthetic listing output without exposing data. Shipping-field probes would
require an order and lack a current display sink, so they are excluded.

## Evidence worksheet

| Evidence | Actual result / reproducibility |
| --- | --- |
| Registration Name passed unchanged to insert with fixed customer role | Offline actual handler PASS; reproducible CLI test; no MySQL write |
| Checkout synthetic stored/session Name stays a single quoted input value | Offline actual template PASS for three names, including quote-boundary marker |
| Product/category/image and reflected search output containment | Offline actual listing template PASS |
| Hosted registration → fresh login → checkout prefill | Pending controlled-account execution |
| Screenshots of minimal form/source/DOM, deployed commit and timestamp | Not collected |
| Fixed comparison, bold unsafe panel versus literal encoded panel | Structure tested; browser screenshot pending; simulation only |

Do not save cookies, CSRF values, passwords, account email addresses, full admin
screens or unrelated customer records in evidence. A rendered name in an input
does not show HTML parsing merely because DevTools displays angle brackets.

## Comparison and remediation

No new executable public endpoint or separate website was created. Reuse the
existing fixed PC Forge-styled comparison generator; it opens a standalone file
directly, has no authentication/customer data, no scripts, forms or network loads,
and accepts no arbitrary unsafe rendering input:

```powershell
python tests/xss_checks.py --php C:/xampp/php/php.exe
$demo = Join-Path $env:TEMP ('pcforge-encoding-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.html')
python tests/xss_checks.py --php C:/xampp/php/php.exe --demo-output $demo
Start-Process $demo
```

The bold panel is fixed hypothetical HTML text rendering, not a vulnerable
checkout. The encoded panel uses the actual e() helper. Proper remediation for
an ordinary text sink is `echo e($name)`; for checkout it is the already present
`value="<?=e(current_user()['name'])?>"`. Store ordinary text without presentation
encoding, then encode on output for the destination context. Stripping tags alone
is not a general replacement. Preserve URL validation as well as attribute escaping.

If live evidence identifies a real unsafe sink, retain the baseline evidence,
patch only that sink, add an actual-template regression and request deployment
approval. Repeat the identical controlled-account steps after deployment and
record its commit. Current code needs no name-output fix based on these tests;
before/after panels must remain explicitly simulated rather than fabricated history.

## Validation and limits

`tests/xss_checks.py` now includes five tests: actual registration insert-boundary,
actual checkout rendering, actual listing/search rendering, actual e() behavior,
and the existing fixed comparison. Registration/database operations are replaced
with in-memory fixtures; checkout is rendered as GET only, never a purchase.
These tests verify the actual template bodies but do not constitute a live Aiven
round-trip, authenticated server test or browser JavaScript execution test.

No SQL/brute-force implementation, production PHP, styling, credentials,
authentication or authorization was modified. No Docker, WSL, local server,
push or deployment was used. See the validation results from this run for syntax
and regression outcomes; live stored-XSS status remains unverified.

Executed results: five XSS tests PASS; all 24 PHP files pass syntax checks with
XAMPP PHP 8.2.12; PHP source/BOM checks PASS; Python compilation and Git whitespace
checks PASS. No failures remain in those executed checks. PHP 8.3/Render behavior,
live account storage and browser evidence were not tested.
