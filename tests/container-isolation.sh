#!/bin/bash
# Executes only disposable containers with synthetic secrets. Requires Docker/curl/openssl.
set -Eeuo pipefail
curl() { command curl --connect-timeout 2 --max-time 10 "$@"; }
cd "$(dirname "$0")/.."
source tests/shell-diagnostics.sh
for executable in docker python3 curl openssl bash mktemp chmod head rm rmdir; do
    if ! type -P "$executable" >/dev/null; then
        isolation_error 127 "$LINENO" "type -P $executable (missing runner executable)" "${BASH_SOURCE[0]}"
        exit 127
    fi
done
work=$(mktemp -d)
disabled=''
enabled=''
unexpected=''
database=''
network="pc-forge-ci-$$-$RANDOM"
cert_volume="$network-certs"
data_volume="$network-data"
container_diagnostics() {
    local container=$1
    docker inspect -f 'id={{.Id}} name={{.Name}} training={{range .Config.Env}}{{if eq . "TRAINING_PREVIEW_ENABLED=1"}}enabled{{end}}{{end}} stop_signal={{.Config.StopSignal}} running={{.State.Running}} exit={{.State.ExitCode}} oom_killed={{.State.OOMKilled}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} error={{json .State.Error}}' "$container" >&2 || true
    docker logs --tail 100 "$container" >&2 || true
}
cleanup() {
    status=$?
    trap - EXIT
    if [[ "$status" != 0 ]]; then
        for container in "$disabled" "$enabled" "$unexpected" "$database"; do
            [[ -z "$container" ]] || container_diagnostics "$container"
        done
    fi
    [[ -z "$disabled" ]] || docker rm -f "$disabled" >/dev/null 2>&1 || true
    [[ -z "$enabled" ]] || docker rm -f "$enabled" >/dev/null 2>&1 || true
    [[ -z "$unexpected" ]] || docker rm -f "$unexpected" >/dev/null 2>&1 || true
    [[ -z "$database" ]] || docker rm -f "$database" >/dev/null 2>&1 || true
    docker volume rm "$cert_volume" "$data_volume" >/dev/null 2>&1 || true
    docker network rm "$network" >/dev/null 2>&1 || true
    rm -f -- "$work/ca.pem" "$work/key.pem"
    rmdir -- "$work"
    exit "$status"
}
trap cleanup EXIT
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$work/key.pem" -out "$work/ca.pem" -days 1 -subj /CN=fixture-db -addext subjectAltName=DNS:fixture-db >/dev/null 2>&1
chmod 600 "$work/ca.pem"
docker build -t pc-forge:isolation-test .
[[ $(docker image inspect -f '{{.Config.StopSignal}}' pc-forge:isolation-test) == SIGTERM ]]
# Check the actual image and the same restricted-PATH identity switch used below.
docker run --rm --entrypoint /bin/sh pc-forge:isolation-test -eu -c '
    test -x /usr/sbin/runuser
    test -x /usr/local/bin/php
    for executable in bash env su install sed apache2ctl apache2-foreground; do
        command -v "$executable"
    done
    env -i PATH=/usr/local/bin:/usr/bin:/bin /usr/sbin/runuser -u pc-training -- env -i PATH=/usr/local/bin:/usr/bin:/bin /usr/local/bin/php -n -r '\''if (getenv("DB_PASSWORD")!==false) { exit(1); } echo "PASS: restricted-PATH runuser/PHP preflight\n";'\''
'
docker network create "$network" >/dev/null
docker volume create "$cert_volume" >/dev/null
docker volume create "$data_volume" >/dev/null
# Only this disposable DB receives the generated key; match its mysql UID.
docker run --rm --user 0:0 --mount "type=bind,src=$work,dst=/fixture,readonly" --mount "type=volume,src=$cert_volume,dst=/certs" --entrypoint sh mysql:8.0 \
    -c 'cp /fixture/ca.pem /certs/ca.pem; cp /fixture/key.pem /certs/key.pem; chown -R mysql:mysql /certs; chmod 600 /certs/key.pem; chmod 644 /certs/ca.pem'
database=$(docker run -d --network "$network" --network-alias fixture-db \
    --mount "type=volume,src=$cert_volume,dst=/certs,readonly" --mount "type=volume,src=$data_volume,dst=/var/lib/mysql" \
    -e MYSQL_ROOT_PASSWORD=synthetic-root-secret -e MYSQL_DATABASE=pc_forge \
    -e MYSQL_USER=synthetic-production-user -e MYSQL_PASSWORD=synthetic-production-secret \
    mysql:8.0 --ssl-ca=/certs/ca.pem --ssl-cert=/certs/ca.pem --ssl-key=/certs/key.pem --require-secure-transport=ON)
db_ready=0
for unused in {1..90}; do
    if docker exec -e MYSQL_PWD=synthetic-root-secret "$database" mysql --protocol=tcp -h127.0.0.1 -uroot --ssl-mode=REQUIRED -e 'SELECT 1' >/dev/null 2>&1; then db_ready=1; break; fi
    if [[ $(docker inspect -f '{{.State.Running}}' "$database") != true ]]; then break; fi
    sleep 1
done
[[ "$db_ready" == 1 ]]
docker exec -i -e MYSQL_PWD=synthetic-root-secret "$database" mysql -uroot < database/schema.sql
docker exec -i -e MYSQL_PWD=synthetic-root-secret "$database" mysql -uroot < tests/fixtures/container-users.sql
hash=$(docker run --rm --entrypoint php pc-forge:isolation-test -r 'echo password_hash("synthetic-instructor-password", PASSWORD_BCRYPT);')
common=(--network "$network" --mount "type=bind,src=$work/ca.pem,dst=/etc/secrets/ca.pem,readonly" -e DB_HOST=fixture-db -e DB_PORT=3306 -e DB_NAME=pc_forge -e DB_SSL_CA=/run/pc-forge/ca.pem -e DB_USER=synthetic-production-user -e DB_PASSWORD=synthetic-production-secret -e TRAINING_DB_USER=synthetic-training-reader -e TRAINING_DB_PASSWORD=synthetic-training-secret -p 127.0.0.1::80)
disabled=$(docker run -d "${common[@]}" pc-forge:isolation-test)
enabled=$(docker run -d "${common[@]}" -e TRAINING_PREVIEW_ENABLED=1 -e TRAINING_INSTRUCTOR_USER=instructor -e "TRAINING_INSTRUCTOR_BCRYPT=$hash" pc-forge:isolation-test)
endpoint() { docker port "$1" 80/tcp | head -1; }
wait_ready() {
    local container=$1
    for unused in {1..60}; do
        if [[ $(docker inspect -f '{{.State.Running}}' "$container") != true ]]; then docker logs "$container"; return 1; fi
        if curl --max-time 2 -s -o /dev/null "http://$(endpoint "$container")/training/"; then return; fi
        sleep 1
    done
    docker logs "$container"
    return 1
}
wait_ready "$disabled"
wait_ready "$enabled"
python3 tests/container_http.py "http://$(endpoint "$disabled")/"
docker exec "$disabled" /usr/sbin/runuser -u www-data -- /usr/local/bin/php -r 'require "/var/www/html/config/db.php";$status=db()->query("SHOW STATUS")->fetchAll(PDO::FETCH_KEY_PAIR);if(empty($status["Ssl_cipher"])){exit(1);}echo "PASS: production PDO connection negotiated TLS to the synthetic MySQL fixture\n";'
[[ $(curl -s -o /dev/null -w '%{http_code}' "http://$(endpoint "$disabled")/training/") == 403 ]]
[[ $(docker exec "$disabled" php -r 'echo is_dir("/run/pc-forge-training/sessions")?"unexpected":"absent";') == absent ]]
[[ $(curl -s -o /dev/null -w '%{http_code}' "http://$(endpoint "$disabled")/login.php") == 200 ]]
[[ $(curl -s -o /dev/null -w '%{http_code}' "http://$(endpoint "$disabled")/assets/style.css") == 200 ]]
for path in training-src/public/index.php docker/training-router.php database/schema.sql; do
    [[ $(curl -s -o /dev/null -w '%{http_code}' "http://$(endpoint "$disabled")/$path") == 403 ]]
done
[[ $(curl -s -H 'X-Forwarded-Proto: https' -o /dev/null -w '%{http_code}' "http://$(endpoint "$enabled")/training/") == 401 ]]
[[ $(curl -s -H 'X-Forwarded-Proto: https' -u instructor:wrong -o /dev/null -w '%{http_code}' "http://$(endpoint "$enabled")/training/") == 401 ]]
# A 200 proves the router received neither Basic auth nor the production cookie.
[[ $(curl -s -H 'X-Forwarded-Proto: https' -H 'Cookie: PHPSESSID=synthetic-production-session' -u instructor:synthetic-instructor-password -o /dev/null -w '%{http_code}' "http://$(endpoint "$enabled")/training/") == 200 ]]
[[ $(curl -s -H 'X-Forwarded-Proto: https' -u instructor:synthetic-instructor-password -d 'email=fixture&password=fixture' -o /dev/null -w '%{http_code}' "http://$(endpoint "$enabled")/training/login.php") == 503 ]]
docker exec -i "$enabled" php < tests/container-probes.php
docker exec "$enabled" env -i PATH=/usr/local/bin:/usr/bin:/bin /usr/sbin/runuser -u pc-training -- env -i PATH=/usr/local/bin:/usr/bin:/bin /usr/local/bin/php -n /usr/local/lib/pc-forge/verify-training.php
# Attempt actual reads as the training UID, without open_basedir masking permissions.
docker exec "$enabled" env -i PATH=/usr/local/bin:/usr/bin:/bin /usr/sbin/runuser -u pc-training -- env -i PATH=/usr/local/bin:/usr/bin:/bin /usr/local/bin/php -n -r 'foreach(["/run/pc-forge/ca.pem","/etc/secrets/ca.pem","/var/www/html/config/db.php","/run/pc-forge-production-sessions/sess_productionfixture123456"] as $p){if(@file_get_contents($p)!==false){exit(1);}}echo "PASS: actual production files and session contents denied to training UID\n";'
# Both the training cookie name and an attempted production-cookie name must fail.
for name in PCFORGE_TRAINING PHPSESSID; do
    [[ $(curl -s -H "Cookie: $name=synthetictrainingadminfixture123456" -o /dev/null -w '%{http_code}' "http://$(endpoint "$enabled")/admin/index.php") == 302 ]]
done
echo 'PASS: forged training admin session cannot authenticate production'
docker exec "$enabled" apache2ctl -t
docker exec "$enabled" /usr/sbin/runuser -u www-data -- /usr/local/bin/php -r '$p=getenv("DB_SSL_CA");if(!is_readable($p)||@openssl_x509_read(file_get_contents($p))===false){exit(1);}echo "PASS: Apache user still reads and parses runtime CA\n";'
# Supervisor must not leave a running public frontend after its backend exits.
docker exec "$enabled" php -r 'foreach(glob("/proc/[0-9]*/cmdline") as $p){$c=@file_get_contents($p);if($c!==false&&str_contains($c,"-S\0"."127.0.0.1:9081")){posix_kill((int)basename(dirname($p)),15);break;}}'
for unused in {1..30}; do
    [[ $(docker inspect -f '{{.State.Running}}' "$enabled") != true ]] && break
    sleep 1
done
[[ $(docker inspect -f '{{.State.Running}}' "$enabled") != true ]]
echo 'PASS: supervisor stops container when training backend exits'
# A malformed instructor configuration must stop startup, not expose a route.
unexpected=$(docker run -d "${common[@]}" -e TRAINING_PREVIEW_ENABLED=1 pc-forge:isolation-test)
for unused in {1..30}; do
    [[ $(docker inspect -f '{{.State.Running}}' "$unexpected") != true ]] && break
    sleep 1
done
[[ $(docker inspect -f '{{.State.Running}}' "$unexpected") != true ]]
[[ $(docker inspect -f '{{.State.ExitCode}}' "$unexpected") != 0 ]]
# Keep the original ten-second limit: fix signal delivery rather than extend it.
[[ "$disabled" != "$enabled" && "$disabled" != "$unexpected" ]]
[[ $(docker inspect -f '{{.State.Running}}' "$disabled") == true ]]
[[ $(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$disabled") != *'TRAINING_PREVIEW_ENABLED=1'* ]]
container_diagnostics "$disabled"
stop_started=$SECONDS
stop_result=0
docker stop --time 10 "$disabled" >/dev/null || stop_result=$?
printf 'Disabled-training stop: elapsed_seconds=%s docker_stop_status=%s timeout_seconds=10\n' "$((SECONDS-stop_started))" "$stop_result" >&2
container_diagnostics "$disabled"
[[ "$stop_result" == 0 ]]
[[ $(docker inspect -f '{{.State.Running}}' "$disabled") != true ]]
[[ $(docker inspect -f '{{.State.OOMKilled}}' "$disabled") == false ]]
[[ $(docker inspect -f '{{.State.ExitCode}}' "$disabled") != 137 ]]
[[ $(docker inspect -f '{{.State.ExitCode}}' "$disabled") == 0 ]]
echo 'PASS: normal container shutdown completes without timeout/SIGKILL'
echo 'PASS: startup/default disable, instructor gate, cookie separation, UID/env/file/session probes'
echo 'NOT VERIFIED: real independent training DB credentials, TLS and restricted grants. Preview has no DB connection. Vulnerable authentication must remain absent.'
