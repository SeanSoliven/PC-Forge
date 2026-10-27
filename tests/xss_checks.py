"""Offline actual-template XSS regression; PHP CLI only, no server or database."""
import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--php', default='C:/xampp/php/php.exe' if Path('C:/xampp/php/php.exe').is_file() else 'php')
parser.add_argument('--demo-output', help='Optional new HTML file outside repository; fixed synthetic comparison only')
args = parser.parse_args()


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.text = []
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
    def handle_data(self, data):
        self.text.append(data)


def php(code, stdin=''):
    result = subprocess.run([args.php, '-r', code], input=stdin, text=True, capture_output=True, cwd=ROOT)
    if result.returncode:
        raise RuntimeError('PHP CLI fixture failed (no live connection attempted)')
    return result.stdout


def encoded(value):
    return php("require 'config/db.php'; echo e(stream_get_contents(STDIN));", value)


ATTRIBUTE_CASES = (
    ('double', '"', '" title="Synthetic boundary'),
    ('single', "'", "' title='Synthetic boundary"),
)


def attribute_examples():
    sections = []
    for label, quote, value in ATTRIBUTE_CASES:
        # Only these fixed inert literals are interpolated without encoding.
        before = '<input readonly value=' + quote + value + quote + '>'
        after = '<input readonly value=' + quote + encoded(value) + quote + '>'
        sections.append('<section class="panel"><h2>' + label.capitalize() + '-quoted attribute</h2>'
                        '<p>Fixed input: <code>' + html.escape(value) + '</code></p>'
                        '<p>Before: quote closes the value; a synthetic title attribute appears.</p>' + before +
                        '<pre>' + html.escape(before) + '</pre>'
                        '<p>After: entire marker remains the value, with no added title attribute.</p>' + after +
                        '<pre>' + html.escape(after) + '</pre></section>')
    return ''.join(sections)


def comparison():
    # Fixed literal markup only: no supplied string ever reaches an unsafe sink.
    safe = encoded('<b>XSS Test</b>')
    css = (ROOT/'assets/style.css').read_text(encoding='utf-8')
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'none'; form-action 'none'; base-uri 'none'">
<title>PC Forge — fixed encoding comparison</title><style>''' + css + '''</style>
<header class="top"><span class="brand">PC<span>FORGE</span></span></header><main class="wrap">
<h1>Fixed HTML encoding comparison</h1><p>Teaching example only. Not a finding against Render. No scripts, network requests, forms or credentials.</p>''' + attribute_examples() + '''
<section class="panel"><h2>Original production behavior</h2><p>Search uses a quoted input value encoded with e(). A bold tag remains text inside that input.</p></section>
<section class="panel"><h2>Hypothetical unsafe HTML text sink</h2><p>Fixed synthetic literal rendered as markup:</p><div id="unsafe"><b>XSS Test</b></div></section>
<section class="panel"><h2>Encoded HTML text sink</h2><div id="safe">''' + safe + '''</div><p>The same bytes become literal text. Production already applies this encoding.</p></section>
<p>HTML rendering proves markup interpretation, not JavaScript execution. Do not deploy this comparison.</p></main></html>'''


class XssChecks(unittest.TestCase):
    def test_double_and_single_attribute_boundaries_before_after(self):
        for label, quote, value in ATTRIBUTE_CASES:
            with self.subTest(context=label):
                before = Document('<input value=' + quote + value + quote + '>').elements[0][1]
                after = Document('<input value=' + quote + encoded(value) + quote + '>').elements[0][1]
                self.assertIn('title', before)
                self.assertNotEqual(before['value'], value)
                self.assertNotIn('title', after)
                self.assertEqual(after['value'], value)

    def test_ampersands_entities_and_tags_are_data(self):
        for value in ('A & B', '&quot; <b>XSS Test</b>', '" single\' < > &'):
            with self.subTest(value=value):
                result = encoded(value)
                self.assertIn('&amp;', result)
                self.assertEqual(html.unescape(result), value)
                self.assertFalse(any(t == 'b' for t,a in Document('<p>' + result + '</p>').elements))

    def test_invalid_utf8_is_replaced_not_dropped(self):
        result = php("require 'config/db.php'; echo bin2hex(e(\"A\\xFFB\"));")
        self.assertEqual(result, '41efbfbd42')

    def test_actual_registration_preserves_synthetic_name_for_storage(self):
        source = (ROOT/'register.php').read_text(encoding='utf-8')
        source = source.replace("require __DIR__.'/bootstrap.php';", '', 1)
        source = source.replace("require __DIR__.'/layout.php';", '', 1)
        config = (ROOT/'config/db.php').read_text(encoding='utf-8')
        config = config.replace('function db(): PDO', 'function unused_fixture_db(): PDO', 1)
        config = config.replace('function redirect($to)', 'function unused_fixture_redirect($to)', 1)
        bootstrap = (ROOT/'bootstrap.php').read_text(encoding='utf-8')
        config += '\nfunction input(' + bootstrap.split('function input(', 1)[1].split('function current_user()', 1)[0]
        with tempfile.TemporaryDirectory(prefix='pcforge-register-xss-') as temp:
            work = Path(temp)
            (work/'helpers.php').write_text(config, encoding='utf-8')
            (work/'template.php').write_text(source, encoding='utf-8')
            setup = '''require $argv[1];
class RegistrationStatement { function execute($params){
 if($params[0]!=='<b>XSS Test</b>')throw new RuntimeException('Name changed');
 if(!password_verify('synthetic-password-only',$params[2]))throw new RuntimeException('Password contract');
 echo 'synthetic-name-accepted-for-insert';
}}
class RegistrationDatabase {function prepare($sql){
 if(!str_contains($sql,"INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'customer')"))throw new RuntimeException('Storage contract');
 return new RegistrationStatement;
}}
function db(){return new RegistrationDatabase;}
function redirect($to){exit;}
$_SESSION=['csrf'=>str_repeat('a',64)]; $_SERVER['REQUEST_METHOD']='POST';
$_POST=['csrf'=>$_SESSION['csrf'],'name'=>'<b>XSS Test</b>','email'=>'synthetic@example.test','password'=>'synthetic-password-only'];
require $argv[2];'''
            result = subprocess.run([args.php, '-r', setup, str(work/'helpers.php'), str(work/'template.php')],
                                    text=True, capture_output=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, 'synthetic-name-accepted-for-insert')

    def test_actual_checkout_encodes_stored_account_name(self):
        source = (ROOT/'checkout.php').read_text(encoding='utf-8')
        source = source.replace("require __DIR__.'/bootstrap.php';", '', 1)
        source = source.replace("__DIR__.'/layout.php'", json.dumps((ROOT/'layout.php').as_posix()))
        with tempfile.TemporaryDirectory(prefix='pcforge-checkout-xss-') as temp:
            path = Path(temp)/'checkout.php'; path.write_text(source, encoding='utf-8')
            for name in ('<b>XSS Test</b>', '\"><b>XSS Test</b><input title="', "Synthetic ' & \" name"):
                setup = '''require 'config/db.php';
$storedName=stream_get_contents(STDIN);
function current_user(){global $storedName; return ['id'=>1,'name'=>$storedName,'role'=>'customer'];}
function require_login(){} function cart_count(){return 1;}
$_SESSION=['cart'=>[1=>1],'csrf'=>str_repeat('a',64),'checkout_token'=>str_repeat('b',64)];
$_SERVER['REQUEST_METHOD']='GET'; require $argv[1];'''
                result = subprocess.run([args.php, '-r', setup, str(path)], input=name, text=True, capture_output=True, cwd=ROOT)
                self.assertEqual(result.returncode, 0)
                doc = Document(result.stdout)
                fields = [a for t,a in doc.elements if t=='input' and a.get('name')=='name']
                self.assertEqual(len(fields), 1)
                self.assertEqual(fields[0]['value'], name)
                self.assertFalse(any(t in ('b','script') or 'title' in a or any(k.startswith('on') for k in a) for t,a in doc.elements))

    def test_real_helper_encodes_quotes_and_markup(self):
        value = '\"\' <b>XSS Test</b> &'
        result = encoded(value)
        self.assertNotIn('<b>', result)
        self.assertNotIn('"', result)
        self.assertNotIn("'", result)
        self.assertEqual(html.unescape(result), value)

    def test_actual_search_template_with_synthetic_database_results(self):
        source = (ROOT/'index.php').read_text(encoding='utf-8')
        self.assertIn("require __DIR__.'/bootstrap.php';", source)
        source = source.replace("require __DIR__.'/bootstrap.php';", '', 1)
        # Keep actual layout and e(); replace only DB access with an in-memory fixture.
        config = (ROOT/'config/db.php').read_text(encoding='utf-8')
        self.assertEqual(config.count('function db(): PDO'), 1)
        config = config.replace('function db(): PDO', 'function unused_fixture_db(): PDO', 1)
        marker = '<b>XSS Test</b>'
        for query in ('Ryzen', '', '  Ryzen  ', marker, '\"><b>XSS Test</b><input title="', "' & < >", 'A & B'):
            with self.subTest(query=query), tempfile.TemporaryDirectory(prefix='pcforge-xss-') as temp:
                work = Path(temp)
                (work/'helpers.php').write_text(config, encoding='utf-8')
                # index.php retains its original __DIR__ for real layout inclusion.
                source_for_fixture = source.replace("__DIR__.'/layout.php'", json.dumps((ROOT/'layout.php').as_posix()))
                (work/'template.php').write_text(source_for_fixture, encoding='utf-8')
                setup = '''require $argv[1];
function current_user(){return null;} function cart_count(){return 0;}
class FixtureRows { private $rows; function __construct($rows){$this->rows=$rows;} function execute($params){
 $expected='%'.trim($_GET['q']).'%';
 if($params!==['cat'=>0,'cat2'=>0,'q'=>$expected,'q2'=>$expected])throw new RuntimeException('Search parameters changed');
} function fetchAll(){return $this->rows;} }
class FixtureDatabase {
function query($sql){return new FixtureRows([['id'=>1,'name'=>'<b>XSS Test</b>']]);}
function prepare($sql){return new FixtureRows([['id'=>1,'name'=>'<b>XSS Test</b>','category'=>'<b>XSS Test</b>','image_url'=>'https://example.invalid/image?x=" title="marker','price'=>1,'stock'=>1]]);}
}
function db(){return new FixtureDatabase;}
$_GET=['q'=>stream_get_contents(STDIN),'cat'=>'0']; require $argv[2];'''
                result = subprocess.run([args.php, '-r', setup, str(work/'helpers.php'), str(work/'template.php')],
                                        input=query, text=True, capture_output=True, cwd=ROOT)
                self.assertEqual(result.returncode, 0, 'Actual template must render in fixture')
                doc = Document(result.stdout)
                search = [a for t, a in doc.elements if t == 'input' and a.get('name') == 'q']
                self.assertEqual(len(search), 1)
                self.assertEqual(search[0]['value'], query.strip())
                self.assertFalse(any(t in ('b', 'script') for t, a in doc.elements))
                self.assertFalse(any('title' in a or any(k.startswith('on') for k in a) for t, a in doc.elements))
                self.assertIn(marker, ''.join(doc.text))

    def test_fixed_comparison_has_only_expected_markup(self):
        doc = Document(comparison())
        self.assertEqual(sum(tag == 'b' for tag, _ in doc.elements), 1)
        self.assertFalse(any(tag in ('script', 'iframe', 'form', 'img') for tag, _ in doc.elements))
        self.assertIn('<b>XSS Test</b>', ''.join(doc.text))


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(XssChecks))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.demo_output:
        destination = Path(args.demo_output).resolve()
        if destination.is_relative_to(ROOT):
            parser.error('Keep comparison artifact outside the repository and hosting root')
        with destination.open('x', encoding='utf-8') as output:
            output.write(comparison())
        print('Created fixed script-free comparison; open the requested file directly in your browser.')
