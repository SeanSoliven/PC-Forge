# GitHub Actions: Linux isolation tests without Docker on your laptop

## Run #1: exit 127 diagnosis and fix

The [actual Docker job log](https://github.com/SeanSoliven/PC-Forge/actions/runs/40350955406/job/121670582025)
shows `env: 'runuser': No such file or directory` at the original
tests/container-isolation.sh line 89. The command used
`env -i PATH=/usr/local/bin:/usr/bin:/bin runuser ...`, but Debian installs the
existing executable at `/usr/sbin/runuser`. The supervisor already used that
absolute path successfully. MySQL, the image build, synthetic logins, verified
TLS, instructor proxy checks, and distinct worker UIDs had already passed. This
was a test PATH bug, not a missing MySQL client or a startup interpreter error.

All test runuser calls now use `/usr/sbin/runuser`, and PHP calls following that
identity switch use `/usr/local/bin/php`. An image preflight checks the required
executables and exercises the same restricted-PATH launch before database setup.
The restrictive PATH and every identity/secret/session assertion are retained.
The shell files had no CRLF or BOM; .gitattributes now preserves their LF endings.

The log also exposed a denied root read of `/proc/.../environ` that the probe
incorrectly cast into an empty string. The probe no longer reports an unreadable
environment as a pass. The actual preview router now rejects unexpected process
environment names before returning content, so the existing authenticated HTTP
200 check tests that guard. A local polluted-environment HTTP test verifies denial.

Failure logging now reports file, line, original exit status and shell-quoted
source command, plus a GitHub error annotation. It does not enable shell xtrace
or expand runtime credential variables into diagnostics. Regression tests force
missing-command exit 127 and failed-assertion exit 1, checking both status
preservation and that a synthetic secret value is not expanded in the log.

These fixes are locally validated, not yet rerun in GitHub Actions. Do not count
the original partially successful Docker run as a completed isolation gate.

Workflow: `.github/workflows/isolation.yml`, named **PC Forge isolation and
regressions**. It runs on GitHub-hosted `ubuntu-24.04` runners when a pull request
is opened/updated or when manually dispatched. No local Docker Desktop or WSL is
required.

## What runs

Two independent jobs run:

1. **PHP 8.3 and synthetic database regressions** installs PHP 8.3 and MariaDB on
   the disposable runner. It checks PHP bytes/syntax, Bash syntax, throttling and
   safe-preview behavior, then runs the existing authentication, admin, cart,
   checkout, rollback, cookie, SQL safety, and error-handling regression suite.
   The suite initializes its own temporary MariaDB datadir/socket/port, uses a
   generated TLS certificate, and never contacts an existing database server.
2. **Linux Docker startup and isolation gate** runs the existing
   `bash tests/container-isolation.sh`. It builds the production Dockerfile and
   creates an isolated MySQL 8.0 fixture container, private Docker network and
   named volumes. A fresh one-day certificate for `fixture-db` provides verified
   TLS to the application. Only the existing synthetic schema seeds and
   `tests/fixtures/container-users.sql` are imported.

The Docker job starts disabled-preview, enabled-safe-preview, and malformed-config
application containers. It checks homepage/product queries, real synthetic
customer/admin logins and authorization, session persistence, default disablement,
separate live worker UIDs, environment clearing, production secret/session-file
denial, production-cookie stripping, forged training-cookie rejection, CA access
and modes, instructor authentication, Apache configuration, and supervisor exit.
It prints failure line numbers and synthetic container logs before cleanup.

All fixture passwords are explicitly synthetic and committed as public test data.
Private keys and certificates are generated per run, never committed or uploaded.
No test uses GitHub repository secrets, production Aiven configuration, real CA
files, customer data, or the public Render hostname. Database ports are not
published; application ports are loopback-only. The script deletes its containers,
named volumes, network, temporary keys and certificates on exit.

## No deployment or Git push capability

The workflow requests only `contents: read`, uses a commit-pinned checkout action
with `persist-credentials: false`, and has no deployment environment, Render API,
deploy hook, Docker registry push, Git push, or repository-secret references.
It uses ordinary pull_request, not pull_request_target. No workflow inputs can
substitute database hosts or credentials. GitHub documents the permission model
at [GITHUB_TOKEN permissions](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token).

Existing Render Git auto-deploy settings are outside this workflow. Your own push
to a Render-watched branch may still trigger that independent integration. Use a
feature branch and pull request for review; this implementation does not push or
modify those settings.

## View results

1. Include the workflow **and all supporting infrastructure/test files** in a
   feature-branch commit, then open/update its pull request. This workspace also
   contains earlier uncommitted infrastructure files; publishing only the YAML
   will not provide the dependencies it needs. No push was performed here.
2. In `SeanSoliven/PC-Forge`, open **Actions → PC Forge isolation and regressions**,
   or open the pull request's **Checks** tab.
3. Select a run, then either named job. Expand the failed step to see assertions,
   PHP errors, build output or the synthetic container diagnostics.
4. The run summary includes each job's status. Green means those runner checks
   passed; cancelled/skipped runs do not count as verification. Fork pull requests
   may require maintainer approval before jobs start.
5. Once the workflow exists on the default branch, you can also select **Run
   workflow**, choose a branch, and run it manually. GitHub requires the definition
   on the default branch for manual dispatch; see [manual workflow runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

If GitHub Actions is disabled for the repository, enable the permitted Actions in
repository settings. This workflow needs no Aiven/Render/GitHub personal tokens or
additional repository secrets.

## What green does not establish

The preview still has no database connection or functional authentication. Its
login POST returns 503. Vulnerable SQL injection and training brute-force code
remain absent. The gate compares **synthetic credential markers only**; independent
real training DB credentials, TLS, least-privilege grants, inherited roles, denied
production access, and actual Render mount/proxy behavior require separate
verification. A green CI run does not deploy or authorize enabling vulnerable code.

## Local validation performed for this change

- Workflow YAML parsed and policy assertions checked: PASS (read-only permissions,
  PR/manual triggers, pinned checkout, no secret references, shell-step syntax).
- PHP syntax/BOM checks and Bash syntax: PASS.
- Throttling/source-policy and safe-preview HTTP checks: PASS on PHP 8.2.12.
- Existing full regression suite, including the new container HTTP helper and
  synthetic account SQL, against disposable local MariaDB over TLS: PASS.
- Actual GitHub-hosted run, Docker image build, MySQL-container TLS startup,
  Linux datadir initialization, and Linux UID/file probes: NOT RUN locally.

Run #1 passed the PHP job and failed the Docker job as described above. No remote
run was dispatched by the assistant. The corrected full Linux gate still requires
a new run after the fix is published; no push or deployment was performed here.
