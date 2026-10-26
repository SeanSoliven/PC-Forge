# PC Forge — PHP + Aiven MySQL storefront

## 1. Aiven
Create a **MySQL** service in Aiven. From its overview, copy host, port, username, password and CA certificate. Aiven commonly provides `defaultdb` already; easiest is to import `database/schema.sql` with an account allowed to create databases. If your account cannot create databases, remove the first two SQL lines and import into an existing database; set DB_NAME accordingly.

In DBeaver: connect to Aiven MySQL with SSL enabled and CA certificate configured; open SQL Editor, paste schema.sql, execute script.

## 2. Run locally (XAMPP)
Copy folder to `C:\xampp\htdocs\pc-forge`. PHP needs pdo_mysql enabled. Supply environment variables DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSL_CA to Apache/PHP (or configure your local Apache environment). Do not commit secrets. DB_SSL_CA should point to the Aiven CA PEM file on the server. Open http://localhost/pc-forge/.

## 3. Deploy
Use a PHP-capable host (e.g. a PHP Apache Docker container on Render); Aiven hosts only the database, **not** your PHP website. Set the same environment variables on your PHP host, and mount the Aiven CA file as a secret. Require HTTPS on the deployed storefront. On Aiven, allow the application host's network access according to your service's network configuration.

### Render Docker configuration

Keep the Render Secret File named `ca.pem` (mounted at `/etc/secrets/ca.pem`).
Set `DB_SSL_CA=/run/pc-forge/ca.pem` and `DB_NAME=pc_forge` in the Render service environment.
Keep `DB_HOST`, `DB_PORT`, `DB_USER`, and `DB_PASSWORD` set to the Aiven connection values.
Use the Dockerfile's default startup command; remove any Render Docker Command override
that bypasses `start-pc-forge`. Save the environment changes and redeploy the service.

At each container startup, root copies the mounted CA into `/run/pc-forge/ca.pem`
with ownership `root:www-data` and mode `640`; the directory has mode `755`.
Startup validates readability and certificate parsing as `www-data` before starting Apache.
Missing, empty, unreadable, or invalid certificates stop startup. PHP also validates the CA
before connecting and keeps SSL server certificate verification enabled.
The CA stays outside Apache's document root. Production PHP hides errors from visitors
and logs errors to container stderr, visible in private Render service logs.
This deployment process does not import a schema or change any database records.

## 4. Admin account
Register a normal account first. Then in DBeaver, run `UPDATE users SET role='admin' WHERE email='YOUR_REGISTERED_EMAIL';` (replace with your own email). Log out and log in again. Never expose an admin registration option publicly.

## Notes
This is a starter demo, not a production-ready store. Checkout supports COD and a **manual bank transfer placeholder**, with no gateway, shipping carrier, email confirmations, or payment verification integration. Session-based cart is used; `cart_items` is reserved for future persistent carts. Product images are illustrative remote URLs. Test and harden before accepting real orders: HTTPS, trusted image hosting, rate limits, server-side validation, persistent cart, secure session cookies, CSRF, auditing, and shipping/payment workflows. The checkout transaction locks product rows and decrements inventory atomically.


## Audit and verification
See `AUDIT.md` for the repair findings, exact local checks, deployment verification, and limitations.
`database/inspect.sql` inspects only `pc_forge` schema metadata without changing records.
Do not import `database/schema.sql` into an existing production database as a repair.
The isolated HTTP regression suite is `tests/integration.py` (Python 3.12+, PHP with pdo_mysql/openssl, MariaDB, OpenSSL).
