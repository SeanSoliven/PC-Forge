"""Offline diagnostics/secret-redaction tests. No Render or Apache process required."""
import argparse
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--php',default='C:/xampp/php/php.exe');args=p.parse_args()
code='''require 'docker/xss-demo-diagnostics.php';
$env=['XSS_DEMO_ENABLED'=>'1','XSS_DEMO_TESTER_USER'=>'private_tester_marker','XSS_DEMO_TESTER_BCRYPT'=>password_hash('private_password_marker',PASSWORD_BCRYPT,['cost'=>8]),'XSS_DEMO_EXPIRES_AT'=>'1800003600','DB_PASSWORD'=>'private_db_marker','RENDER_GIT_COMMIT'=>str_repeat('a',40)];
$lines=implode("\\n",xss_demo_diagnostic_lines($env,1800000000));
foreach (['private_tester_marker','private_password_marker','private_db_marker',$env['XSS_DEMO_TESTER_BCRYPT'],$env['XSS_DEMO_EXPIRES_AT']] as $secret) {if(str_contains($lines,$secret))exit(1);}
if(!str_contains($lines,'enabled=yes reason=enabled') || !str_contains($lines,'expiry=valid') || !str_contains($lines,'commit='.str_repeat('a',40)))exit(2);
$env['XSS_DEMO_TESTER_BCRYPT']='secret-invalid-hash';$env['RENDER_GIT_COMMIT']='secret-invalid-commit';
$lines=implode("\\n",xss_demo_diagnostic_lines($env,1800000000));
if(str_contains($lines,'secret-') || !str_contains($lines,'reason=invalid-bcrypt') || !str_contains($lines,'commit=unavailable'))exit(3);
$env['XSS_DEMO_TESTER_BCRYPT']=password_hash('synthetic',PASSWORD_BCRYPT,['cost'=>8]);
$lines=implode("\\n",xss_demo_diagnostic_lines($env,1800003601));if(!str_contains($lines,'reason=expired'))exit(4);
if(xss_demo_include_status("Included configuration files:\\n  (*) /etc/apache2/apache2.conf\\n    (225) /etc/apache2/conf-enabled/pc-forge-xss.conf\\nSyntax OK",0)!=='loaded')exit(5);
if(xss_demo_include_status('Syntax OK',0)!=='NOT-LOADED')exit(6);
if(xss_demo_include_status('error includes private text',1)!=='syntax-or-includes-failed')exit(7);
if(xss_demo_include_status('Error: /etc/apache2/conf-enabled/pc-forge-xss.conf',0)!=='NOT-LOADED')exit(8);
echo "PASS: safe flags/revision/commit; secret redaction; expiry; included, missing and failed Apache config\\n";'''
subprocess.run([args.php,'-r',code],cwd=ROOT,check=True)
startup=(ROOT/'docker/start-pc-forge').read_text()
assert startup.index('prepare-xss-demo.php') < startup.index('verify-xss-apache.php') < startup.index('exec /usr/local/bin/supervise-pc-forge')
build=(ROOT/'Dockerfile').read_text()
for file in ('xss-demo-diagnostics.php','verify-xss-apache.php'):
    assert 'COPY docker/'+file+' /usr/local/lib/pc-forge/'+file in build
assert 'CMD ["start-pc-forge"]' in build
print('PASS: Dockerfile packages diagnostics; loaded-config gate runs after generation, before Apache supervisor')
