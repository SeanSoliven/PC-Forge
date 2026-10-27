<?php
declare(strict_types=1);
if (PHP_SAPI!=='cli') { http_response_code(404); exit; }
require __DIR__.'/xss-demo-diagnostics.php';
// Fixed command, no environment values or secrets in arguments or logged output.
$output=[]; $code=1;
exec('/usr/sbin/apache2ctl -t -D DUMP_INCLUDES 2>&1',$output,$code);
$status=xss_demo_include_status(implode("\n",$output),$code);
echo 'PC Forge XSS Apache config='.$status.PHP_EOL;
if ($status!=='loaded') {
    fwrite(STDERR,"PC Forge startup error: XSS route policy is not confirmed loaded; refusing unchecked Apache startup.\n");
    exit(1);
}
$config=@file_get_contents('/etc/apache2/conf-enabled/pc-forge-xss.conf');
if (!is_string($config)) { fwrite(STDERR,"PC Forge startup error: generated XSS policy unreadable.\n"); exit(1); }
$auth=str_contains($config,'Require valid-user');
$deny=str_contains($config,'^/xss-demo(?:/|$)');
if ($auth===$deny || !str_contains($config,'Alias "/xss-demo/" "/opt/pc-forge-xss/"')) {
    fwrite(STDERR,"PC Forge startup error: unrecognized XSS authorization policy or missing Alias.\n"); exit(1);
}
echo 'PC Forge XSS loaded policy='.($deny?'denied':'tester-authentication').' alias=present'.PHP_EOL;
