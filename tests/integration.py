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
import socket
import subprocess
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
    result = subprocess.run([args.php], input='<?php\n' + code, text=True,
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
        env.update(DB_HOST='localhost', DB_PORT=str(dbport), DB_NAME='pc_forge_test',
                   DB_USER='root', DB_PASSWORD='', DB_SSL_CA=str(cert), RENDER='false')
        log = open(work / 'server.log', 'w', encoding='utf-8')
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        server = subprocess.Popen([args.mysqld, '--no-defaults', '--datadir=' + str(data),
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
        setup = '''$p=new PDO('mysql:host=localhost;port='.getenv('DB_PORT'), 'root', '', [PDO::MYSQL_ATTR_SSL_CA=>getenv('DB_SSL_CA'), PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT=>true]);
$sql=file_get_contents('database/schema.sql');
$sql=str_replace(['CREATE DATABASE IF NOT EXISTS pc_forge ', 'USE pc_forge;'], ['CREATE DATABASE IF NOT EXISTS pc_forge_test ', 'USE pc_forge_test;'], $sql);
$p->exec($sql);
echo 'fixture ready';'''
        check(php(setup, env) == 'fixture ready', 'repository schema imported into disposable TLS database')
        phpserver = subprocess.Popen([args.php, '-d', 'session.save_path=' + str(sessions), '-d', 'display_errors=0', '-d',
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
        check(customer.request('login.php', fields)[0] == 422, 'incorrect password rejected')
        fields['password'] = 'test-password-123'
        old_session = [(c.name, c.value) for c in customer.cookies]
        status, _, headers = customer.request('login.php', fields)
        check(status == 302 and headers['Location'] == 'index.php', 'customer login redirect')
        check(old_session != [(c.name, c.value) for c in customer.cookies], 'session regenerated after login')
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
