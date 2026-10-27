"""Offline validation of hosted fixed-payload policy and startup/auth configuration."""
import argparse
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--php',default='C:/xampp/php/php.exe');args=p.parse_args()
code='''require 'xss-demo-src/render.php'; require 'docker/xss-demo-config.php';
foreach (['vulnerable','fixed'] as $version) {
 parse_str('version='.$version,$parsed);if(xss_demo_value($parsed)!==[$version,''])exit(14);
 if(xss_demo_value(['version'=>$version])!==[$version,''])exit(10);
 foreach ([['version'=>$version],['version'=>$version,'q'=>'']] as $initial) {
  http_response_code(200);ob_start();xss_render($initial);$page=ob_get_clean();
  if(http_response_code()!==200 || !str_contains($page,'<style>') || !str_contains($page,'type="search"') || !str_contains($page,'value=""') || !str_contains($page,'vulnerable Reflected') || !str_contains($page,'fixed Reflected') || substr_count($page,'<article')!==3 || str_contains($page,'Predefined synthetic inputs only.'))exit(11);
 }
}
if(xss_demo_value([])!==['fixed',''])exit(12);
foreach ([['version'=>'vulnerable','q'=>'unapproved'],['version'=>'fixed','q'=>[]],['version'=>'vulnerable','extra'=>'tracking'],['version'=>[]]] as $invalid) {
 http_response_code(200);ob_start();xss_render($invalid);$page=ob_get_clean();
 if(http_response_code()!==400 || !str_contains($page,'<style>') || !str_contains($page,'Predefined synthetic inputs only.') || str_contains($page,'tracking') || str_contains($page,'unapproved') || str_contains($page,'<script>'))exit(13);
}
echo ''; // Keep header calls testable until final output.
foreach ([[],['q'=>"<script>alert('XSS Demonstration Successful')</script>"],['version'=>'vulnerable','q'=>"\\\" onclick=\\\"alert('XSS Demonstration Successful')\\\" data-demo=\\\""]] as $ok) {xss_demo_value($ok);}
foreach ([['q'=>'<script>fetch(1)</script>'],['q'=>[]],['version'=>'other'],['unexpected'=>'x']] as $bad) {
 try {xss_demo_value($bad);exit(1);}catch(InvalidArgumentException $e){}
}
$enabled=xss_demo_apache_config(true);$disabled=xss_demo_apache_config(false);
foreach (['Require valid-user','AuthUserFile','RequestHeader unset Cookie',"X-Forwarded-Proto",'Header always unset Set-Cookie'] as $check) {
 if(!str_contains($enabled,$check))exit(2);
}
if(!str_contains($disabled,'Require all denied') || !str_contains($disabled,'Alias "/xss-demo/" "/opt/pc-forge-xss/"'))exit(3);
ob_start();xss_render(['version'=>'fixed','q'=>"<script>alert('XSS Demonstration Successful')</script>"]);$fixed=ob_get_clean();
if(str_contains($fixed,'<script>') || !str_contains($fixed,'&lt;script&gt;'))exit(4);
ob_start();xss_render(['version'=>'vulnerable','q'=>"<script>alert('XSS Demonstration Successful')</script>"]);$vulnerable=ob_get_clean();
if(!str_contains($vulnerable,"<script>alert('XSS Demonstration Successful')</script>"))exit(5);
echo "PASS: both initial pages, empty payload, styled 400 recovery, exact synthetic payloads, arbitrary input denial, disabled-default/auth config and encoding comparison\\n";'''
# Rendering fixture gets the same CSS file used by the build, without a live server.
import tempfile
with tempfile.TemporaryDirectory() as temp:
    work=Path(temp)
    (work/'render.php').write_text((ROOT/'xss-demo-src/render.php').read_text(),encoding='utf-8')
    (work/'style.css').write_text((ROOT/'assets/style.css').read_text(),encoding='utf-8')
    code=code.replace("'xss-demo-src/render.php'",repr((work/'render.php').as_posix()))
    subprocess.run([args.php,'-r',code],cwd=ROOT,check=True)
result=subprocess.run([args.php,str(ROOT/'xss-demo-src/index.php')],capture_output=True,text=True)
assert result.stdout=='Demonstration unavailable.','Direct CLI entry must fail closed'
print('PASS: non-Apache direct entry denied; live Apache/auth/browser gates remain untested')
