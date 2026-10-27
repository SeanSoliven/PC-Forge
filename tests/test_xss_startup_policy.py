"""Pure startup policy and diagnostic regression; no Apache/Render/filesystem mutation."""
import argparse
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--php',default='C:/xampp/php/php.exe');args=p.parse_args()
code='''require 'docker/xss-demo-config.php';
$now=1800000000;
$env=['XSS_DEMO_ENABLED'=>'1','XSS_DEMO_TESTER_USER'=>'tester','XSS_DEMO_TESTER_BCRYPT'=>password_hash('synthetic',PASSWORD_BCRYPT,['cost'=>8]),'XSS_DEMO_EXPIRES_AT'=>(string)($now+3600)];
if(xss_demo_configuration_status($env,$now)!==[true,'enabled'])exit(1);
foreach (['XSS_DEMO_ENABLED'=>'not-enabled','XSS_DEMO_TESTER_USER'=>'invalid-tester-name','XSS_DEMO_TESTER_BCRYPT'=>'invalid-bcrypt','XSS_DEMO_EXPIRES_AT'=>'invalid-expiry'] as $name=>$reason) {
 $bad=$env;unset($bad[$name]);if(xss_demo_configuration_status($bad,$now)!==[false,$reason])exit(2);
}
$bad=$env;$bad['XSS_DEMO_EXPIRES_AT']=(string)($now-1);if(xss_demo_configuration_status($bad,$now)!==[false,'expired'])exit(3);
$bad['XSS_DEMO_EXPIRES_AT']=(string)($now+28801);if(xss_demo_configuration_status($bad,$now)!==[false,'expiry-over-eight-hours'])exit(4);
foreach ([true,false] as $enabled) {if(!str_contains(xss_demo_apache_config($enabled),'Alias "/xss-demo/" "/opt/pc-forge-xss/"'))exit(5);}
$config=xss_demo_apache_config(true);
if(str_contains($config,'^/xss-demo(?:/|$)') || !str_contains($config,'Require valid-user') || !str_contains($config,'AuthMerging Off'))exit(6);
if(str_contains($config,'Require all granted'))exit(7);
echo "PASS: enabled, missing, invalid and expired settings; stable Alias; tester authentication retained\\n";'''
subprocess.run([args.php,'-r',code],cwd=ROOT,check=True)
