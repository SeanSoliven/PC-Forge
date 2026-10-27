# PC Forge search: HTML attribute before/after comparison

Target: `https://pc-forge-k68s.onrender.com`. Date: 2026-10-28 (Asia/Manila).
This assessment uses source and offline PHP CLI tests. No requests were sent to
Render, no executable payload was added and no push/deployment was performed.

## Actual application baseline

`index.php:1` takes `q` from GET, defaults to an empty string and applies trim.
It does not apply a search length limit or an explicit scalar type check; an array
input can raise a type error rather than becoming an XSS payload. The category
parameter is cast to integer. Search binds `%q%` to the existing name/description
LIKE parameters. These queries and their behavior were not modified.

`index.php:3` reflects search only in this **double-quoted HTML attribute**:

```php
<input name="q" value="<?=e($q)?>" placeholder="Search computer parts...">
```

There is no search reflection into a text node or JavaScript context. The page's
other ordinary attributes are double-quoted; single quotes around PHP array keys,
SQL or PHP strings are not HTML attribute delimiters. Conditional static attributes
such as selected/disabled do not contain the search string. `layout.php` also uses
double-quoted attributes and escapes the title in a text node. `bootstrap.php`
initializes sessions/security headers and imports the helper; it does not reflect
search text itself. No application JavaScript or DOM search sink was found.

Before this change `e()` in `config/db.php` already called htmlspecialchars with
ENT_QUOTES and UTF-8. Therefore **no original search XSS is confirmed**. The
actual production before/after change is UTF-8 handling hardening, not removal
of an established successful exploit. ENT_SUBSTITUTE replaces malformed input
bytes with U+FFFD rather than losing the output string.

Production bootstrap has nosniff, Referrer-Policy, no-store and cookie protections,
but no source-defined CSP/frame policy. Training-route CSP is separate. Actual
Render CSP remains unverified. CSP is defense in depth, not a substitute for output
encoding; a meta CSP cannot enforce frame-ancestors.

## What quotes and encoding do

Surrounding quotes delimit a value; they do not encode data. An unescaped matching
quote can terminate the value and make following text into attributes or elements.
The other quote type does not close that particular delimiter, but ENT_QUOTES
encodes both, so the helper works in both quoted ordinary attribute contexts.
Never use these examples to justify unquoted attributes.

Hypothetical unsafe code (comparison only; not installed in index.php):

```php
<input value="<?= $q ?>">
<input value='<?= $q ?>'>
```

Secure code and the updated shared helper:

```php
function e($v): string {
    return htmlspecialchars((string) $v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
// Both retain a single value containing the original valid text:
<input value="<?= e($q) ?>">
<input value='<?= e($q) ?>'>
```

An entity such as `&quot;` is decoded as a quote **inside the attribute value** by
the HTML parser; it does not retroactively close the attribute. A DOM value showing
quotes or angle brackets is therefore normal and is not itself an injection.
HTML escaping is not a universal encoder for JavaScript/CSS or a URL scheme policy.

## Fixed synthetic cases

| Input | Hypothetical unescaped result | Properly encoded result |
| --- | --- | --- |
| `<b>XSS Test</b>` in a text sink | b element, bold text | Literal text, no b element |
| `<b>XSS Test</b>` inside a quoted value | Usually remains value text; alone does not break quotes | Entire literal value stays intact |
| `" title="Synthetic boundary` inside double quotes | Value ends early; extra inert title attribute | One value, no added title |
| `' title='Synthetic boundary` inside single quotes | Value ends early; extra inert title attribute | One value, no added title |
| `A & B` | Ampersand may participate in entity parsing depending on suffix | `A &amp; B`, DOM round-trips to original |
| `&quot; <b>XSS Test</b>` | Entity/markup interpretation in a text sink | Original entity-looking text preserved through `&amp;quot;` |
| Invalid UTF-8 byte FF between A and B | Prior helper can return empty output | A, replacement character, B |

The quote cases are malformed relative to the intended single-attribute structure;
the browser can recover by creating a syntactically valid additional attribute.
They use no scripts, event handlers, network destinations or customer data.
HTML injection and JavaScript execution are distinct findings.

## Demonstration and screenshots

No new site, localhost server, Docker, WSL or Render deployment is needed. Reuse
the fixed comparison generator with PC Forge CSS, stored outside the repository:

```powershell
python tests/xss_checks.py --php C:/xampp/php/php.exe
$demo = Join-Path $env:TEMP ('pcforge-attributes-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.html')
python tests/xss_checks.py --php C:/xampp/php/php.exe --demo-output $demo
Start-Process $demo
```

The artifact contains only fixed synthetic literals. No supplied input reaches an
unescaped sink. It has a script-blocking CSP, read-only inputs, no forms, external
resources or credentials. Do not publish it to the production origin.

Capture these screenshots:

1. Double-quoted panel: truncated unsafe value and source with added title, then
   encoded source and complete secure value. DevTools Elements confirms attributes.
2. Equivalent single-quoted panel, showing the matching delimiter boundary.
3. Hypothetical unsafe bold text versus secure literal markup. Label it simulation.
4. Separately, when authorized to perform the live check, the actual Render search
   using `<b>XSS Test</b>` and its raw encoded response. Expect literal search data.
   Record the actual deployed commit, browser and UTC timestamp. No live check
   occurred in this implementation.

Do not use customer records or capture cookies, credentials or CSRF values. Do not
remove e() from production to manufacture the unsafe baseline. Repeat identical
harmless searches after any approved deployment; record the already-protected
baseline honestly, and keep simulated unsafe examples separate.

## Changes and validation

Modified `config/db.php`: only helper flags changed to ENT_QUOTES | ENT_SUBSTITUTE.
No connection settings, credentials, auth logic, SQL/brute-force code, index markup
or CSS changed. The shared helper affects rendering wherever used; valid UTF-8
output is unchanged, malformed sequences now become replacement characters.

Extended `tests/xss_checks.py` and its existing fixed comparison with both quote
contexts and explicit unsafe/secure structure checks. Eight tests PASS using
XAMPP PHP 8.2.12: double/single boundaries, tag/ampersand/entity handling, malformed
UTF-8 replacement, original helper behavior, actual search/listing template,
registration insert boundary, checkout encoding, and fixed artifact structure.
Several cases are grouped in the eight test methods.

Search tests check ordinary/empty/trimmed queries and markup/quote/ampersand inputs,
assert original category/name/description parameter bindings, preserve original
display values and parse the actual template output. DB rows are synthetic fixture
results: this proves binding/rendering behavior, not real MySQL LIKE semantics or
live Render behavior. No database or HTTP server is started by these checks.

Additional validation PASS: syntax checks on all 24 PHP files, PHP source/BOM
checks, two existing CLI CSRF/ownership tests, Python compilation and Git whitespace
checks. PHP 8.3, live database search results, Render browser screenshots and actual
deployment remain untested in this run.

Recommended remediation is contextual output encoding at every HTML sink; the
search already uses it. Additional scalar/length validation and CSP policy can
be reviewed separately without changing SQL or authentication workstreams.
