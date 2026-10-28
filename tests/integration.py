"""Isolated HTTP integration suite. Requires PHP, MariaDB server and OpenSSL.

Example on Windows:
python tests/integration.py --php C:/xampp/php/php.exe --mysqld C:/xampp/mysql/bin/mysqld.exe --openssl "C:/Program Files/Git/usr/bin/openssl.exe"

Only a new temporary datadir is used; inherited DB_* settings are replaced.
No existing database server is contacted. No production accounts are created.
"""
import argparse
import http.cookiejar
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--php', default='php')
parser.add_argument('--mysqld', default='mysqld')
parser.add_argument('--openssl', default='openssl')
args = parser.parse_args()
processes = []
temporary_directory = tempfile.TemporaryDirectory(prefix='pc-forge-audit-', delete=False)
log = None


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    print('PASS:', name, flush=True)


def php(code, env):
    result = subprocess.run([args.php, '-d', 'output_buffering=0'], input='<?php\n' + code, text=True,
                            capture_output=True, env=env, cwd=ROOT)
    if result.returncode:
        raise RuntimeError('Fixture PHP failed: ' + result.stderr)
    return result.stdout.strip()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *unused):
        return None


class Browser:
    def __init__(self, base):
        self.base = base
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies), NoRedirect())

    def request(self, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        try:
            response = self.opener.open(self.base + path, body, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        return response.code, response.read().decode('utf-8'), response.headers

    def form(self, path):
        status, body, headers = self.request(path)
        check(status == 200, 'GET ' + path)
        fields = dict(re.findall(r'name="(csrf|checkout_token)" value="([^"]+)"', body))
        check('csrf' in fields, 'CSRF form ' + path)
        return fields


try:
    with temporary_directory as temporary:
        work = Path(temporary).resolve()
        data = work / 'mysql'
        data.mkdir()
        sessions = work / 'sessions'
        sessions.mkdir()
        cert = work / 'ca.pem'
        key = work / 'server.key'
        result = subprocess.run([args.openssl, 'req', '-x509', '-newkey', 'rsa:2048',
                                 '-nodes', '-keyout', str(key), '-out', str(cert),
                                 '-days', '1', '-subj', '/CN=localhost', '-addext',
                                 'subjectAltName=DNS:localhost,IP:127.0.0.1'], capture_output=True)
        check(result.returncode == 0, 'generate disposable TLS certificate')
        dbport, webport = port(), port()
        env = os.environ.copy()
        env.update(DB_HOST='127.0.0.1', DB_PORT=str(dbport), DB_NAME='pc_forge_test',
                   DB_USER='root', DB_PASSWORD='', DB_SSL_CA=str(cert), RENDER='false')
        check(php("require 'config/db.php';if(headers_sent()){exit(1);}echo 'quiet';", env) == 'quiet', 'db include emits no output with buffering disabled')
        probe = "session_save_path(" + repr(str(sessions).replace('\\', '/')) + ");require 'bootstrap.php';echo session_status()===PHP_SESSION_ACTIVE && !headers_sent()?'active':'failed';"
        check(php(probe, env) == 'active', 'session starts before output with PHP buffering disabled')
        log = open(work / 'server.log', 'w', encoding='utf-8')
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        if os.name != 'nt':
            installer = shutil.which('mariadb-install-db') or shutil.which('mysql_install_db')
            if not installer:
                raise RuntimeError('Install mariadb-server: an isolated datadir initializer is required on Linux.')
            initialized = subprocess.run([installer, '--no-defaults', '--datadir=' + str(data),
                                          '--auth-root-authentication-method=normal', '--skip-test-db'],
                                         stdout=log, stderr=log)
            if initialized.returncode:
                log.flush()
                raise RuntimeError('Temporary MariaDB datadir initialization failed: ' + (work / 'server.log').read_text(errors='replace'))
        server = subprocess.Popen([args.mysqld, '--no-defaults', '--datadir=' + str(data),
                                   *([] if os.name == 'nt' else ['--socket=' + str(work / 'mysql.sock'), '--pid-file=' + str(work / 'mysql.pid')]),
                                   '--port=' + str(dbport), '--bind-address=127.0.0.1',
                                   '--skip-grant-tables', '--skip-log-bin',
                                   '--innodb-buffer-pool-size=32M', '--ssl-ca=' + str(cert),
                                   '--ssl-cert=' + str(cert), '--ssl-key=' + str(key)],
                                  stdout=log, stderr=log, creationflags=flags)
        processes.append(server)
        for attempt in range(100):
            if server.poll() is not None:
                raise RuntimeError('Temporary MariaDB startup failed; ' + (work / 'server.log').read_text())
            try:
                with socket.create_connection(('127.0.0.1', dbport), timeout=.2):
                    break
            except OSError:
                time.sleep(.1)
        setup = '''$p=new PDO('mysql:host=127.0.0.1;port='.getenv('DB_PORT'), 'root', '', [PDO::MYSQL_ATTR_SSL_CA=>getenv('DB_SSL_CA'), PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT=>true]);
$sql=file_get_contents('database/schema.sql');
$sql=str_replace(['CREATE DATABASE IF NOT EXISTS pc_forge ', 'USE pc_forge;'], ['CREATE DATABASE IF NOT EXISTS pc_forge_test ', 'USE pc_forge_test;'], $sql);
$p->exec($sql);
echo 'fixture ready';'''
        check(php(setup, env) == 'fixture ready', 'repository schema imported into disposable TLS database')
        phpserver = subprocess.Popen([args.php, '-d', 'output_buffering=0', '-d', 'session.save_path=' + str(sessions), '-d', 'display_errors=0', '-d',
                                      'log_errors=1', '-S', '127.0.0.1:' + str(webport),
                                      '-t', str(ROOT)], env=env, stdout=log, stderr=log,
                                     creationflags=flags)
        processes.append(phpserver)
        base = 'http://127.0.0.1:' + str(webport) + '/'
        customer = Browser(base)
        for attempt in range(50):
            try:
                status, body, headers = customer.request('login.php')
                break
            except OSError:
                time.sleep(.1)
        check(status == 200, 'login page')
        check('HttpOnly' in headers.get('Set-Cookie', '') and 'SameSite=Lax' in headers.get('Set-Cookie', ''), 'session cookie flags')
        status, body, _ = customer.request('index.php')
        check(status == 200 and 'Ryzen 5 7600' in body, 'product listing through verified TLS')
        check('No products found.' in customer.request('index.php?cat=99999')[1], 'empty category state')
        check(customer.request('admin/index.php')[0] == 302, 'anonymous admin redirected')
        fields = customer.form('register.php')
        fields.update(name='Test Customer', email='customer@example.test', password='test-password-123', role='admin')
        check(customer.request('register.php', fields)[0] == 302, 'valid registration')
        query = "require 'config/db.php';$p=db();"
        check(php(query + "$s=$p->query(\"SHOW STATUS LIKE 'Ssl_cipher'\")->fetch();echo $s['Value'];", env) != '', 'database connection uses negotiated TLS')
        check(php(query + "$u=$p->query('SELECT password_hash,role FROM users LIMIT 1')->fetch();echo password_verify('test-password-123',$u['password_hash'])&&$u['role']==='customer'?'ok':'bad';", env) == 'ok', 'password stored as hash and role forced to customer')
        status, body, _ = customer.request('register.php', fields)
        check(status == 422 and 'already exists' in body, 'duplicate-email registration')
        fields = customer.form('login.php')
        fields.update(email='customer@example.test', password='incorrect')
        check(customer.request('login.php', fields)[0] == 302, 'incorrect password rejected and redirected to status')
        check('4 attempts remaining.' in customer.request('login.php')[1], 'first failure shows remaining attempts')
        check(customer.request('login.php', dict(fields, email="customer@example.test' OR '1'='1"))[0] == 302, 'production prepared login rejects SQL injection payload')
        fields['password'] = 'test-password-123'
        old_session = [(c.name, c.value) for c in customer.cookies]
        status, _, headers = customer.request('login.php', fields)
        check(status == 302 and headers['Location'] == 'index.php', 'customer login redirect')
        check(old_session != [(c.name, c.value) for c in customer.cookies], 'session regenerated after login')
        check(php(query + "$key=hash('sha256','account:customer@example.test');$s=$p->prepare('SELECT failed_attempts FROM login_attempts WHERE account_key=?');$s->execute([$key]);echo $s->fetchColumn();", env) == '0', 'successful login resets failed attempt count')
        check(customer.request('admin/index.php')[0] == 403, 'customer forbidden from admin; registration ignored submitted admin role')
        check(customer.request('admin/index.php', {'action': 'stock', 'id': 1, 'stock': 999})[0] == 403, 'customer admin POST forbidden')
        fields = customer.form('index.php')
        fields.update(action='add', product_id=1)
        check(customer.request('cart.php', fields)[0] == 302, 'add to cart')
        check(customer.request('cart.php', dict(fields, csrf='invalid'))[0] == 422, 'cart CSRF enforced')
        fields.update(action='update', quantity=2)
        check(customer.request('cart.php', fields)[0] == 302, 'update cart quantity')
        fields['quantity'] = 9999
        check(customer.request('cart.php', fields)[0] == 422, 'cart stock limit enforced')
        checkout = customer.form('checkout.php')
        checkout.update(name='Test Customer', phone='09123456789', address='123 Test Street, Manila', method='cod')
        check(customer.request('checkout.php', dict(checkout, address='short'))[0] == 422, 'checkout address validation')
        php(query + "$p->exec('UPDATE products SET stock=0 WHERE id=1');", env)
        check(customer.request('checkout.php', checkout)[0] == 422, 'checkout rechecks stock under lock')
        check(php(query + "echo $p->query('SELECT COUNT(*) FROM orders')->fetchColumn();", env) == '0', 'failed checkout leaves no order')
        php(query + "$p->exec('UPDATE products SET stock=12 WHERE id=1');", env)
        php(query + "$p->exec('RENAME TABLE payments TO payments_unavailable');", env)
        status, body, _ = customer.request('checkout.php', checkout)
        check(status == 500 and 'SQLSTATE' not in body, 'checkout SQL failure returns safe error')
        check(php(query + "echo $p->query('SELECT COUNT(*) FROM orders')->fetchColumn().':'.$p->query('SELECT stock FROM products WHERE id=1')->fetchColumn().':'.$p->query('SELECT COUNT(*) FROM order_items')->fetchColumn();", env) == '0:12:0', 'checkout rollback removes partial order and restores stock')
        php(query + "$p->exec('RENAME TABLE payments_unavailable TO payments');", env)
        status, _, headers = customer.request('checkout.php', checkout)
        check(status == 302 and headers['Location'].startswith('orders.php?placed='), 'checkout creates order')
        check(customer.request('checkout.php', checkout)[0] == 302, 'checkout replay redirected with empty cart')
        result = php(query + "echo json_encode([$p->query('SELECT COUNT(*) FROM orders')->fetchColumn(),$p->query('SELECT stock FROM products WHERE id=1')->fetchColumn(),$p->query('SELECT quantity FROM order_items LIMIT 1')->fetchColumn(),$p->query('SELECT status FROM payments LIMIT 1')->fetchColumn()]);", env)
        import json
        check(json.loads(result) == [1, 10, 2, 'unpaid'], 'single order, stock decrement, order line and manual payment record')
        order_id = int(php(query + "echo $p->query('SELECT id FROM orders LIMIT 1')->fetchColumn();", env))
        check('Test Customer' not in customer.request('orders.php')[1] and customer.request('orders.php')[0] == 200, 'order history loads')
        php(query + "$p->exec(\"INSERT INTO users(name,email,password_hash,role) VALUES('Test Admin','admin@example.test','\".password_hash('admin-password-123', PASSWORD_DEFAULT).\"','admin')\");", env)
        admin = Browser(base)
        fields = admin.form('login.php')
        fields.update(email='admin@example.test', password='admin-password-123')
        status, _, headers = admin.request('login.php', fields)
        check(status == 302 and headers['Location'] == 'admin/index.php', 'admin login redirect')
        check(admin.request('admin/index.php')[0] == 200, 'admin dashboard loads')
        check(f'<td>#{order_id}</td>' not in admin.request('orders.php')[1], 'order history restricted to owning user')
        fields = admin.form('admin/index.php')
        fields.update(action='add', name='Fixture GPU', category_id=2, price='99.95', stock=5, description='Fixture only', image_url='https://example.test/gpu.png')
        check(admin.request('admin/index.php', fields)[0] == 302, 'admin creates validated product')
        check(admin.request('admin/index.php', dict(fields, image_url='javascript:alert(1)'))[0] == 422, 'unsafe product image URL rejected')
        fields.update(action='stock', id=1, stock=9)
        check(admin.request('admin/index.php', fields)[0] == 302, 'admin stock update')
        fields.update(action='status', id=order_id, status='processing')
        check(admin.request('admin/index.php', fields)[0] == 302, 'admin order status update')
        check('processing' in customer.request('orders.php')[1], 'customer sees updated order status')
        fields.update(action='payment', status='paid')
        check(admin.request('admin/index.php', fields)[0] == 302, 'admin manual payment status update')
        fields.update(action='status', status='cancelled')
        check(admin.request('admin/index.php', fields)[0] == 302, 'unshipped order cancellation')
        check(php(query + "echo $p->query('SELECT stock FROM products WHERE id=1')->fetchColumn();", env) == '11', 'cancelled order restores inventory')
        check(admin.request('admin/index.php', fields)[0] == 302, 'repeated cancellation is idempotent')
        check(php(query + "echo $p->query('SELECT stock FROM products WHERE id=1')->fetchColumn();", env) == '11', 'repeated cancellation does not restore stock twice')
        check(admin.request('admin/index.php', dict(fields, status='processing'))[0] == 422, 'cancelled order cannot reopen without inventory reservation')
        php(query + "$p->exec(\"UPDATE users SET role='customer' WHERE email='admin@example.test'\");", env)
        check(admin.request('admin/index.php')[0] == 403, 'admin demotion enforced without new login')
        fields = customer.form('index.php')
        fields.update(action='add', product_id=2)
        check(customer.request('cart.php', fields)[0] == 302, 'add another product')
        old_checkout = customer.form('checkout.php')
        fields.update(action='update', quantity=2)
        check(customer.request('cart.php', fields)[0] == 302, 'cart mutation invalidates checkout token')
        old_checkout.update(name='Customer', phone='09123456789', address='123 Test Street, Manila', method='cod')
        check(customer.request('checkout.php', old_checkout)[0] == 422, 'stale checkout form rejected')
        fields.update(action='remove')
        check(customer.request('cart.php', fields)[0] == 302 and 'Cart is empty.' in customer.request('cart.php')[1], 'remove cart product')
        check(customer.request('logout.php')[0] == 405, 'logout requires POST')
        check(customer.request('logout.php', {'csrf': 'invalid'})[0] == 403, 'logout requires CSRF')
        fields = customer.form('orders.php')
        check(customer.request('logout.php', fields)[0] == 302, 'logout destroys session')
        check(customer.request('orders.php')[0] == 302, 'orders require login after logout')
        fields = customer.form('login.php')
        fields.update(email='throttle-fixture@example.test', password='incorrect')
        for remaining in (4, 3, 2, 1):
            check(customer.request('login.php', fields)[0] == 302, 'failed login redirects to attempt status')
            check(f'{remaining} attempt' in customer.request('login.php')[1], 'remaining-attempt message updates')
        check(customer.request('login.php', fields)[0] == 302, 'fifth failed login starts cooldown')
        status, body, _ = customer.request('login.php')
        check(status == 200 and 'Too many failed login attempts.' in body, 'cooldown message is displayed')
        expiration = re.search(r'data-lockout-until="(\d+)"', body).group(1)
        check('id="login-button" disabled' in body and 'assets/login.js' in body, 'login is disabled and countdown script is loaded')
        check(re.search(r'try again in \d{2}:\d{2}\.', body) is not None, 'cooldown is displayed as MM:SS')
        check(re.search(r'data-lockout-until="(\d+)"', customer.request('login.php')[1]).group(1) == expiration, 'refresh keeps server lockout expiration')
        fresh = Browser(base)
        fresh_fields = fresh.form('login.php')
        fresh_fields.update(email='throttle-fixture@example.test', password='incorrect')
        check(fresh.request('login.php', fresh_fields)[0] == 302, 'new browser session cannot reset production account throttle')
        fresh_body = fresh.request('login.php')[1]
        check(re.search(r'data-lockout-until="(\d+)"', fresh_body).group(1) == expiration, 'server enforces same account expiry across browser sessions')
        php(query + "$p->exec(\"UPDATE login_attempts SET locked_until=UNIX_TIMESTAMP()-1 WHERE account_key='\".hash('sha256','account:throttle-fixture@example.test').\"'\");", env)
        check('Too many failed login attempts.' not in customer.request('login.php')[1], 'expired cooldown clears on server status check')
        # Both protected names here exist ONLY inside the disposable local fixture.
        # Run scripts with an unrelated default schema to catch unqualified writes.
        safety = php(query + '''
foreach (['pc_forge','mens_daydb'] as $name) {
 $p->exec("CREATE DATABASE `$name`");
 $p->exec("CREATE TABLE `$name`.users (name VARCHAR(30))");
 $p->exec("INSERT INTO `$name`.users VALUES ('untouched')");
 $p->exec("CREATE TABLE `$name`.products (stock INT)");
 $p->exec("INSERT INTO `$name`.products VALUES (77)");
}
$p->exec('USE pc_forge');
$p->exec(file_get_contents('training-src/database/setup.sql'));
$p->exec("UPDATE pc_forge_training.users SET role='admin' WHERE email='customer@training.test'");
$p->exec('UPDATE pc_forge_training.products SET stock=0');
$p->exec('USE mens_daydb');
$p->exec(file_get_contents('training-src/database/reset.sql'));
foreach (['pc_forge','mens_daydb'] as $name) {
 if ($p->query("SELECT name FROM `$name`.users")->fetchColumn()!=='untouched' || (int)$p->query("SELECT stock FROM `$name`.products")->fetchColumn()!==77) { exit(1); }
}
echo $p->query("SELECT role FROM pc_forge_training.users WHERE email='customer@training.test'")->fetchColumn().':'.$p->query("SELECT stock FROM pc_forge_training.products WHERE name='Synthetic CPU'")->fetchColumn();
''', env)
        check(safety == 'customer:12', 'training setup/reset target only qualified synthetic tables, even with protected default schemas')
        php(query + "$p->exec(str_replace('pc_forge.users',getenv('DB_NAME').'.users',file_get_contents('tests/fixtures/container-users.sql')));", env)
        contract = subprocess.run([sys.executable, str(ROOT / 'tests/container_http.py'), base],
                                  text=True, capture_output=True)
        if contract.returncode:
            raise RuntimeError('Container HTTP fixture contract failed: ' + contract.stdout + contract.stderr)
        print(contract.stdout, end='', flush=True)
        check(True, 'Docker HTTP helper also passes against local synthetic TLS fixture')
        # A separate PHP process exercises missing/invalid configuration safely.
        for changes, label in [({'DB_HOST': ''}, 'missing DB configuration'),
                               ({'DB_SSL_CA': ''}, 'missing SSL configuration'),
                               ({'DB_SSL_CA': str(work / 'missing.pem')}, 'missing CA file'),
                               ({'DB_SSL_CA': str(ROOT / 'Dockerfile')}, 'invalid PEM')]:
            testenv = dict(env, **changes)
            result = php("require 'config/db.php';try {db();exit(1);}catch(RuntimeException $e){echo $e->getMessage();}", testenv)
            check(result == 'Database connection unavailable', label + ' fails safely')
        # Force an actual query failure, proving the former blank-page path responds safely.
        php(query + "$p->exec('RENAME TABLE categories TO categories_unavailable');", env)
        status, body, _ = customer.request('index.php')
        check(status == 500 and 'Something went wrong' in body and 'SQLSTATE' not in body and str(ROOT) not in body, 'unexpected SQL failure returns safe nonblank HTTP 500')
        log.flush()
        server_log = (work / 'server.log').read_text(encoding='utf-8')
        check('headers already sent' not in server_log and 'Session cannot be started' not in server_log and 'Session ini settings cannot be changed' not in server_log, 'no header or session initialization warnings in HTTP regression logs')
        print('PASS: integration suite complete', flush=True)
        # Stop services before TemporaryDirectory removes only its own verified temp path.
        for process in reversed(processes):
            process.terminate()
            process.wait(timeout=15)
        processes.clear()
        log.close()
finally:
    for process in reversed(processes):
        process.terminate()
        process.wait(timeout=15)
    if log:
        log.close()
    temporary_directory.cleanup()
