# Aiven shared-service training database: manual setup and verification

The existing Aiven MySQL service may host all three schemas. Only
`pc_forge_training` is used for training. `pc_forge` and `mens_daydb` must remain
inaccessible to the dedicated training user. No commands in this guide have been
run against Aiven by the assistant. The backend remains disabled and unchanged.

## Scope and minimum permissions

The supported contract is read-only: retrieve synthetic account hashes/roles and
product rows. It requires exactly SELECT on `pc_forge_training.users` and
`pc_forge_training.products`. No schema wildcard, writes, roles, global privileges,
FILE, administrative rights or grant option are needed. Attempts/auditing/reset
are not runtime DB operations; reset is an owner-only manual operation. Future
write features need a separate review, not broader grants now.

Schema grants isolate data access, not the shared service's CPU, memory or
availability. Any later injectable-query demonstration still needs bounded query
time/attempt budgets and resource review. This preparation does not certify
unrestricted testing as safe for a service that also hosts production databases.

The verifier is a trusted **CLI-only operator tool**, not a web endpoint or the
training process. It never writes records or grants, changes server settings, or
enables training. Its only connection-state change is a denied USE probe. A
successful probe would fail verification without reading production records.

## 1. Check Aiven's user-management capability

[Aiven's service-user documentation](https://aiven.io/docs/products/mysql/howto/manage-service-users)
says new service users are administrative by default. Its creation API accepts
`mysql_grants: []` for connection-only access. Granular creation requires service
support; unsupported services return HTTP 400. Do not omit the field, select
default Console/CLI creation, or create an administrator and rely on later cleanup.

In Aiven Console, open the existing MySQL service and **Connect → Users** to
inspect existing users. Reserve the new name `pc_forge_training_reader`; it must
not be the production DB_USER. If it already exists, stop and audit it rather than
reusing it blindly. Check with an authorized owner that mandatory roles will not
automatically give the new account access outside training. Do not change global
roles/settings shared with production.

## 2. Create the synthetic schema

Connect your trusted SQL client to the existing service as an authorized owner,
with CA and server-hostname verification enabled. Run `setup.sql` once. Every
table operation is explicitly qualified with `pc_forge_training`, regardless of
the client's default schema. The script intentionally does not use DROP or
IF NOT EXISTS to conceal an existing database.

Stop on the first error. Do not use mysql --force or a client configured to ignore
errors. A duplicate database requires inspection, not deleting any existing data.
Do not import the storefront's database/schema.sql as a training repair.

## 3. Create the user with zero privileges

Preferred: use Aiven's documented API with the committed, non-secret payload
`aiven-user-request.json`. From PowerShell, after setting project/service/token
privately in your current environment:

```powershell
$created = Invoke-RestMethod -Method Post `
  -Uri "https://api.aiven.io/v1/project/$env:AIVEN_PROJECT/service/$env:AIVEN_SERVICE/user" `
  -Headers @{ Authorization = "Bearer $env:AIVEN_TOKEN" } `
  -ContentType 'application/json' `
  -Body (Get-Content -Raw training-src/database/aiven-user-request.json)
```

Do not print/publish `$created`: the response can contain the generated password.
Store it privately in your password manager. The API token is an operator token;
never add it to Render or the training application. Remove the token from your
shell environment when finished. No secrets go in the JSON request file.

If granular creation returns HTTP 400, stop and ask Aiven support about capability
and any required maintenance. Do not apply maintenance automatically on a shared
production service. If a SQL-only creation path is explicitly supported for your
service/operator, `create-user.sql` is an alternative: MySQL generates a random
password and requires SSL. It needs account-management permission which must NOT
be assumed for every Aiven account. Choose one creation path, never both.

Console steps alone are acceptable only if they explicitly support an empty
privilege list; the documented generic Add service user flow is not a least-
privilege guarantee. If Aiven prevents exact table grants, keep training disabled
and request a supported restricted-user procedure from support. Never substitute
global SELECT, CREATE USER or ROLE_ADMIN.

## 4. Grant only two tables

Using the authorized owner, inspect:

```sql
SHOW GRANTS FOR 'pc_forge_training_reader'@'%';
```

Confirm the account host with Aiven if it differs from `%`; do not grant a second
host account accidentally. Before grants, expect only connection-level USAGE and
no roles. If grants are broader, stop. This procedure does not revoke or alter
any existing production account. Never substitute DB_USER/avnadmin for the fixed
reader name.

Run `grants.sql` manually. It requires SSL for the new account and grants SELECT
on precisely two tables. If ALTER USER/GRANT is denied, stop and obtain Aiven's
supported method. Do not assume unrestricted MySQL root privileges or edit mysql
system tables. Keep credentials away from a SQL client's exported connection files.

`USAGE ON *.*` is MySQL's no-privilege connection placeholder, not global SELECT.
The verifier rejects all actual global/dynamic privileges, roles (including
inactive/mandatory assignments), wildcard/column grants, extra tables and grant
option. It uses bare SHOW GRANTS, which includes mandatory roles for the current
user; see [MySQL SHOW GRANTS](https://dev.mysql.com/doc/refman/8.0/en/show-grants.html).
Unrecognized grant output also fails closed and needs review.

## 5. Set independent TRAINING_DB_* variables manually

Keep all existing DB_* variables and `/etc/secrets/ca.pem` unchanged, including:

```ini
DB_NAME=pc_forge
DB_SSL_CA=/run/pc-forge/ca.pem
```

Set these privately in Render (or your trusted local verification shell):

```ini
TRAINING_PREVIEW_ENABLED=0
TRAINING_DB_HOST=<existing Aiven service hostname>
TRAINING_DB_PORT=<existing Aiven service port>
TRAINING_DB_NAME=pc_forge_training
TRAINING_DB_USER=pc_forge_training_reader
TRAINING_DB_PASSWORD=<new Aiven-generated password>
TRAINING_DB_SSL_CA=/etc/secrets/training-ca.pem
```

Add a **separate Render Secret File** named `training-ca.pem` containing the Aiven
CA, without changing the production `ca.pem`. Same service means the CA contents
may be identical; the variables/files remain separate. Do not chmod/move secrets
or pass them into the isolated backend yet. Local verification uses an absolute
local CA path instead of /etc/secrets. Do not save secrets inside this repository,
even though .gitignore excludes common certificate/environment files.

These variables do not enable training. The supervisor still strips all DB values
from the preview process, and its environment guard remains intact. The CLI
helpers are copied outside the document root to /usr/local/lib/pc-forge. No grant
verification was added to automatic startup; no live connection happens on deploy.

## 6. Explicit, read-only verification with the actual reader credentials

On a trusted local PHP CLI installation with pdo_mysql and openssl:

```powershell
php docker/verify-training-db.php --verify
```

Or, after a separately reviewed normal deployment, in a trusted Render operator
shell (not the training user or public browser):

```sh
php /usr/local/lib/pc-forge/verify-training-db.php --verify
```

No connection occurs without `--verify`. No repository .env file is loaded. It
accepts only TRAINING_DB_* values, fixes schema/user names, and rejects reuse of
DB_USER/DB_PASSWORD if those production variables are available for comparison.
Without production variables it cannot compare unknown passwords: generate a new
password rather than reusing one. Runtime CURRENT_USER must be the dedicated
reader account, not an administrative login.

The tool requires a readable parseable CA, native prepares, disabled multi-
statements, and server certificate verification. It confirms a negotiated TLS
cipher/version, exact grants, synthetic account hashes/roles and product reads.
It then requires MySQL access-denied error 1044 for both `USE pc_forge` and
`USE mens_daydb`. No table or customer records in those schemas are queried.
Missing schemas/network failures are failures, not accepted proof of denial.

Require the final VERIFIED line **and process exit zero**, not partial PASS lines.
Errors show only phase/SQLSTATE/driver code, never driver messages, credentials,
raw grants, CA contents or traces. Results apply only to that connection/time;
there is no auto-enable marker. Reverify after credential/grant changes. Keep
TRAINING_PREVIEW_ENABLED=0 until actual verification succeeds and subsequent
backend wiring is separately implemented/reviewed. No vulnerable code exists yet.

## Owner-only reset and tests

`reset.sql` targets only qualified training rows, even when the SQL client defaults
to pc_forge. The reader cannot execute it. No web reset endpoint is provided.

Local policy/config tests: `php tests/training_db_checks.php`. They never connect
to Aiven. GitHub's Docker gate now runs the same verifier against a real limited
user on its disposable MySQL fixture and checks rejection of a wrong CA. All of
those credentials/data are synthetic; no GitHub secret is needed. Existing schema
namespace-safety regression tests remain in place. Actual Aiven verification must
be performed by you explicitly; it has not run here.
