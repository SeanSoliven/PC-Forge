"""CLI-only checks of actual CSRF helper and order-list authorization boundary."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--php', default='C:/xampp/php/php.exe' if Path('C:/xampp/php/php.exe').exists() else 'php')
args = p.parse_args()


def run(code):
    result = subprocess.run([args.php, '-d', 'display_errors=0', '-r', code], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError('PHP fixture failed: ' + result.stderr)
    return result.stdout


class Checks(unittest.TestCase):
    def test_csrf_actual_helper_missing_invalid_array_and_other_session(self):
        code = '''require 'config/db.php'; $_SESSION=['csrf'=>str_repeat('a',64)];
foreach ([[],['csrf'=>'wrong'],['csrf'=>[]],['csrf'=>str_repeat('b',64)]] as $post) {
 $_POST=$post; try {check_csrf(); exit(1);} catch (InvalidArgumentException $e) {}
}
$_POST=['csrf'=>$_SESSION['csrf']]; check_csrf(); echo 'accepted-only-matching-token';'''
        self.assertEqual(run(code), 'accepted-only-matching-token')

    def test_order_template_binds_authenticated_identity_not_supplied_id(self):
        template = (ROOT/'orders.php').read_text()
        template = template.replace("require __DIR__.'/bootstrap.php';", '', 1)
        template = template.replace("require __DIR__.'/layout.php';", '', 1)
        with tempfile.TemporaryDirectory(prefix='pcforge-access-') as folder:
            path = Path(folder)/'orders.php'
            path.write_text(template)
            for account in (101, 202):
                code = '''require 'config/db.php';
function current_user(){return ['id'=>ACCOUNT];} function require_login(){}
function head_html($title){} function foot_html(){}
class Rows implements IteratorAggregate {
 function execute($params){if($params!==[ACCOUNT])throw new RuntimeException('Wrong account binding');}
 function getIterator(): Traversable {return new ArrayIterator([]);}
}
class DatabaseFixture {function prepare($sql){if(!str_contains($sql,'WHERE o.user_id=?'))throw new RuntimeException('Missing ownership predicate');return new Rows;}}
'''
                # Rename unused connection helper in a temporary copy; actual order template is evaluated.
                helper = (ROOT/'config/db.php').read_text().replace('function db(): PDO', 'function unused_db(): PDO', 1)
                helper_path = Path(folder)/'helpers.php'; helper_path.write_text(helper)
                code = code.replace("require 'config/db.php';", 'require '+json.dumps(helper_path.as_posix())+';')
                code += "function db(){return new DatabaseFixture;} $_GET=['id'=>999,'user_id'=>999,'placed'=>999]; require "+json.dumps(path.as_posix())+';'
                self.assertIn('My orders', run(code.replace('ACCOUNT', str(account))))


if __name__ == '__main__':
    unittest.main(argv=['web_security_checks'], verbosity=2)
