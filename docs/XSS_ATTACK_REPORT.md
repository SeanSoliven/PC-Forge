# PC Forge intentional XSS demonstration and retest

## Scope and evidence status

These are intentionally vulnerable **local synthetic examples**, not findings
against `https://pc-forge-k68s.onrender.com`. The real search already uses output
encoding. No production PHP, security helper, authentication, SQL-injection or
brute-force implementation was changed. No Render request, push or deployment was
performed. No database/account/customer information is used by either demo.

The existing `.dockerignore` excludes `tests` from the Render image and `.htaccess`
denies the tests route. Both pages additionally refuse execution outside the
explicitly enabled, loopback-bound PHP CLI server/router. Do not copy these files
to another public web root or remove these safeguards. No Docker or WSL is needed.

## Files and relevant lines

| File | Purpose |
| --- | --- |
| `tests/xss_vulnerable_demo.php` | Two intentionally unsafe output contexts |
| `tests/xss_fixed_demo.php` | Same synthetic search with contextual HTML encoding |
| `tests/xss_demo_support.php` | Loopback/opt-in guards, shared PC Forge styling, fixed synthetic products, independent encoding helper |
| `tests/xss_demo_router.php` | Allowlist of the two pages and existing CSS; everything else 404 |
| `tests/test_xss_demo.py` | Actual local HTTP checks and optional browser dialog checks |

Vulnerable page **line 10**:

```php
<input type="search" name="q" value="<?= $query ?>" placeholder="Search computer parts...">
```

An unescaped matching double quote closes the value; following bytes can become
attributes, including the demonstrated inline click handler.

Vulnerable page **line 14**:

```php
<p id="search-summary">Search results for: <?= $query ?></p>
```

Input enters an HTML text context without encoding, so a submitted script element
is interpreted by the browser. The same script text alone inside the quoted input
does not execute; the separate summary sink makes reflected execution possible.

Fixed page **lines 10 and 14** replace each raw `$query` output with
`demo_escape($query)`. The independent helper in `tests/xss_demo_support.php`
**lines 24–26** is:

```php
function demo_escape(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
```

This encodes quotes, angle brackets and ampersands. The input stays double-quoted;
the text sink displays literal markup. Invalid UTF-8 is replaced. No production
helper is imported or modified. Encoding is the primary fix; the fixed page also
uses `script-src 'none'` as defense in depth. The intentionally vulnerable page
permits inline scripts solely for this demonstration. Both block external scripts,
connect/fetch, images, frames and objects through CSP. No cookies are issued.

## Exact Windows startup

Open PowerShell in the repository root and use a dedicated browser profile with
no production accounts. The server exposes only the isolated examples; do not
serve the repository root or start XAMPP Apache for this exercise.

```powershell
$testRoot = (Resolve-Path .\tests).Path
$demoRouter = Join-Path $testRoot 'xss_demo_router.php'
$env:PCFORGE_XSS_DEMO_ENABLED = '1'
try {
    & C:/xampp/php/php.exe -n -d display_errors=0 -S 127.0.0.1:8099 -t $testRoot $demoRouter
} finally {
    Remove-Item Env:PCFORGE_XSS_DEMO_ENABLED -ErrorAction SilentlyContinue
}
```

Keep that terminal open. **Ctrl+C stops the demo**. Only localhost is bound;
do not substitute `0.0.0.0`, use a tunnel or forward the port. Plain GET is the
only method. Non-scalar or over-512-byte search inputs receive 400. A missing
enable flag, unsupported Host, non-loopback binding or direct execution without
the router receives 403. Production routes are not available on this server.

Initial pages:

- `http://127.0.0.1:8099/xss_vulnerable_demo.php`
- `http://127.0.0.1:8099/xss_fixed_demo.php`

The existing CSS and storefront hero, filters and product cards are reused. Search
matches three fixed synthetic product names in memory. No add-to-cart, login,
orders, storage or production navigation is present.

## Case 1: reflected script execution

Payload (synthetic proof only):

```html
<script>alert('XSS Demonstration Successful')</script>
```

In a second PowerShell terminal, construct and open the URL:

```powershell
$reflected = "<script>alert('XSS Demonstration Successful')</script>"
$encoded = [Uri]::EscapeDataString($reflected)
Start-Process ("http://127.0.0.1:8099/xss_vulnerable_demo.php?q=" + $encoded)
```

Expected browser result: one alert with **XSS Demonstration Successful** when the
summary script executes. Dismiss it before proceeding. Capture the address bar,
alert and PC Forge page, without unrelated browser information. In DevTools
Network inspect the raw response; Elements should show a script node in the
summary. Do not read cookies, credentials or other windows.

Retest the identical payload:

```powershell
Start-Process ("http://127.0.0.1:8099/xss_fixed_demo.php?q=" + $encoded)
```

Expected: no alert, no injected script node, literal payload in the input and
summary. Capture the encoded response (`&lt;script&gt;...`) and rendered text.

## Case 2: quotation-mark attribute injection

Payload:

```text
" onclick="alert('XSS Demonstration Successful')" data-demo="
```

Construct the URL without shell-quoting ambiguity:

```powershell
$attribute = @'
" onclick="alert('XSS Demonstration Successful')" data-demo="
'@
$attributeEncoded = [Uri]::EscapeDataString($attribute.Trim())
Start-Process ("http://127.0.0.1:8099/xss_vulnerable_demo.php?q=" + $attributeEncoded)
```

**Click the search input**, rather than the Search button. Expected: its injected
onclick handler shows the same alert. Capture the alert and, separately, the input
element with its new onclick attribute. This case requires interaction; it does
not depend on browser autofocus behavior. The harmless data-demo attribute absorbs
the original trailing quote.

Retest:

```powershell
Start-Process ("http://127.0.0.1:8099/xss_fixed_demo.php?q=" + $attributeEncoded)
```

Click the fixed search input. Expected: no alert and no onclick attribute; the
entire marker is one value. Raw source contains `&quot;`/`&#039;` where appropriate.
Entity decoding into input.value is normal; decoded quotes are not reparsed as
attribute delimiters. Capture the fixed value and parsed attributes.

## Ordinary behavior and retest worksheet

Search for `Synthetic` on both pages: three product cards should appear. Search
for `Ryzen`: one card. No-match payloads return no matching cards, but the search
summary still shows the query (encoded in the fixed version).

| Test | Expected vulnerable | Expected fixed | Actual evidence this run |
| --- | --- | --- | --- |
| Reflected script | Alert on load | Literal text, no alert | HTTP response and parsed script node verified; browser dialog pending |
| Attribute injection | Alert when input clicked | No handler or alert | HTTP-created onclick and fixed attribute containment verified; browser dialog pending |
| Harmless bold marker | Bold summary | Literal marker | Parsed markup versus encoded data verified |
| Normal synthetic search | Matching cards | Same matching cards | HTTP test PASS |
| Explicit opt-in absent | 403 | 403 | PASS |
| Production/unrelated routes | 404 | 404 | PASS |
| Cookie issuance | None | None | PASS |

Fill in manual browser version, UTC timestamp, screenshots and dialog observations
after performing the steps. Do not label browser execution “confirmed” merely
because a parser found a script element. An alert failure may reflect browser
settings, policy, wrong page or the input not being clicked; retain the actual
result. These local results never establish a production Render vulnerability.

## Automated validation

```powershell
python tests/test_xss_demo.py --php C:/xampp/php/php.exe
python tests/xss_checks.py --php C:/xampp/php/php.exe
python tests/web_security_checks.py --php C:/xampp/php/php.exe
python tests/php_source.py
```

The HTTP suite starts and terminates its own ephemeral loopback server, strips
inherited production DB environment variables, never contacts Render/Aiven, and
tests both pages, contexts, opt-in, Host restrictions, allowed methods, input
limits, unrelated-route denial, styling and deployment exclusions.

Optional if Playwright **and its Chromium browser are already installed**:

```powershell
python tests/test_xss_demo.py --php C:/xampp/php/php.exe --browser
```

This mode checks the actual alert text for both vulnerable cases and its absence
for both fixed cases. Playwright is not installed in this environment, so browser
automation was **not run**. Manual Edge/Chrome steps above require no extra package.

Executed validation: local HTTP/isolation suite PASS; eight existing XSS tests
PASS; two existing CSRF/ownership CLI tests PASS; syntax checks on all 28 PHP files
PASS using XAMPP PHP 8.2.12; source/BOM checks, Python compilation and whitespace
checks PASS. No browser-dialog or production exploit result is claimed.

## Remediation guidance

Preserve quoted attributes and encode on output for the exact context; do not
rely on stripping tags or SQL parameters to prevent XSS. This helper is suitable
for ordinary HTML text/attributes, not arbitrary JavaScript, CSS or URL policy.
For the presentation the fixed page is the patch: the same payloads are replayed
against it. Do not remove production encoding or publish the vulnerable page.
