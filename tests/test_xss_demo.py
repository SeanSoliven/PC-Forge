"""Actual loopback HTTP tests; no production or database access. Optional Playwright browser test."""
import argparse
from html.parser import HTMLParser
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--php', default='C:/xampp/php/php.exe')
p.add_argument('--browser', action='store_true', help='Also verify JS dialogs; requires installed Playwright and Chromium')
args = p.parse_args()
REFLECTED = "<script>alert('XSS Demonstration Successful')</script>"
ATTRIBUTE = '''" onclick="alert('XSS Demonstration Successful')" data-demo="'''


class DOM(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def check(value, label):
    if not value:
        raise AssertionError(label)
    print('PASS:', label, flush=True)


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def browser_checks(base):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            for fixed in (False, True):
                for payload in (REFLECTED, ATTRIBUTE):
                    page = browser.new_page()
                    messages = []
                    def dialog(d):
                        messages.append(d.message); d.dismiss()
                    page.on('dialog', dialog)
                    path = '/xss_fixed_demo.php' if fixed else '/xss_vulnerable_demo.php'
                    page.goto(base + path + '?q=' + urllib.parse.quote(payload, safe=''))
                    if payload == ATTRIBUTE:
                        page.locator('input[name=q]').click()
                    page.wait_for_timeout(300)
                    check(messages == ([] if fixed else ['XSS Demonstration Successful']),
                          ('fixed blocks' if fixed else 'vulnerable executes') + (' attribute handler' if payload == ATTRIBUTE else ' reflected script'))
                    page.close()
        finally:
            browser.close()


with tempfile.TemporaryDirectory(prefix='pcforge-xss-http-') as folder:
    # Avoid inherited production DB_* variables and shared production document root.
    env = {k: os.environ[k] for k in ('PATH', 'SystemRoot', 'TEMP', 'TMP') if k in os.environ}
    number = port()
    base = f'http://127.0.0.1:{number}'
    command = [args.php, '-n', '-d', 'display_errors=0', '-S', f'127.0.0.1:{number}',
               '-t', str(ROOT/'tests'), str(ROOT/'tests/xss_demo_router.php')]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(path, headers=None, data=None):
        req = urllib.request.Request(base + path, headers=headers or {}, data=data)
        try:
            response = opener.open(req, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, response.read().decode(), response.headers
    def start(environment):
        proc = subprocess.Popen(command, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if proc.poll() is not None:
                raise RuntimeError('PHP fixture did not start')
            try:
                request('/xss_fixed_demo.php'); return proc
            except OSError:
                time.sleep(.1)
        proc.terminate(); proc.wait(timeout=10)
        raise RuntimeError('PHP fixture readiness failed')
    process = start(env)
    try:
        check(request('/xss_vulnerable_demo.php')[0] == 403, 'demo disabled without explicit opt-in')
    finally:
        process.terminate(); process.wait(timeout=10)
    env['PCFORGE_XSS_DEMO_ENABLED'] = '1'
    process = start(env)
    try:
        for payload in (REFLECTED, ATTRIBUTE, '<b>XSS Test</b>', '" single\' & < >'):
            for fixed in (False, True):
                path = '/xss_fixed_demo.php' if fixed else '/xss_vulnerable_demo.php'
                status, body, headers = request(path + '?q=' + urllib.parse.quote(payload, safe=''))
                check(status == 200, 'synthetic demo HTTP 200')
                doc = DOM(body)
                attrs = next(a for t,a in doc.tags if t == 'input' and a.get('name') == 'q')
                if fixed:
                    check(attrs['value'] == payload and 'onclick' not in attrs, 'fixed value boundaries preserved')
                    check(not any(t in ('script','b') for t,a in doc.tags), 'fixed markup treated as data')
                    check("script-src 'none'" in headers['Content-Security-Policy'], 'fixed CSP blocks scripts')
                elif payload == REFLECTED:
                    check(any(t == 'script' for t,a in doc.tags), 'vulnerable reflected script exists in parsed HTML')
                elif payload == ATTRIBUTE:
                    check(attrs.get('onclick') == "alert('XSS Demonstration Successful')", 'vulnerable quote creates event handler')
                check(headers.get('Set-Cookie') is None, 'no session cookie issued')
        for forbidden in ('/', '/index.php', '/config/db.php', '/xss_demo_support.php', '/../login.php'):
            check(request(forbidden)[0] == 404, 'router denies unrelated paths')
        check(request('/xss_fixed_demo.php', {'Host': 'unrelated.example'})[0] == 403, 'Host rebinding denied')
        check(request('/xss_fixed_demo.php', data=b'q=test')[0] == 405, 'POST denied')
        check(request('/xss_fixed_demo.php?q='+'x'*513)[0] == 400, 'oversized input denied')
        check(request('/xss_fixed_demo.php?q[]=test')[0] == 400, 'array input denied')
        check(request('/style.css')[0] == 200, 'existing PC Forge styling available')
        for path in ('/xss_fixed_demo.php', '/xss_vulnerable_demo.php'):
            status, body, _ = request(path + '?q=Synthetic')
            check(status == 200 and body.count('<article') == 3, 'ordinary synthetic search still works')
        if args.browser:
            browser_checks(base)
        else:
            print('NOT RUN: real browser JavaScript dialogs (use --browser or manual steps).')
    finally:
        process.terminate(); process.wait(timeout=10)
check('tests' in (ROOT/'.dockerignore').read_text().splitlines(), 'Render build excludes tests directory')
check('training-src|docker|database|tests' in (ROOT/'.htaccess').read_text(), 'production Apache denies tests route')
