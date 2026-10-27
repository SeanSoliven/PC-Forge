<?php
declare(strict_types=1);
// Safe Render Shell diagnostic. Never print environment values, htpasswd or secrets.
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require __DIR__.'/xss-demo-config.php';
[$enabled,$reason]=xss_demo_configuration_status(getenv(),time());
echo 'Current settings: '.($enabled?'enabled':'disabled').' reason='.$reason.PHP_EOL;
$config='/etc/apache2/conf-enabled/pc-forge-xss.conf';
$content=@file_get_contents($config);
echo 'Generated config: '.($content===false?'missing-or-unreadable':'present').PHP_EOL;
if (is_string($content)) {
    echo 'Expected Alias: '.(str_contains($content,'Alias "/xss-demo/" "/opt/pc-forge-xss/"')?'present':'MISSING').PHP_EOL;
    echo 'Tester authentication: '.(str_contains($content,'Require valid-user')?'present':'absent').PHP_EOL;
    echo 'Blanket disabled URL denial: '.(str_contains($content,"^/xss-demo(?:/|$)")?'present':'absent').PHP_EOL;
    echo 'Matches current settings: '.(trim($content)===trim(xss_demo_apache_config($enabled))?'yes':'NO; startup/deployed settings differ').PHP_EOL;
}
foreach (['/var/www/html/xss-demo','/opt/pc-forge-xss','/opt/pc-forge-xss/index.php','/opt/pc-forge-xss/render.php','/opt/pc-forge-xss/style.css','/run/pc-forge-xss-auth','/run/pc-forge-xss-auth/testers'] as $path) {
    clearstatcache(true,$path);
    $stat=@stat($path);
    echo $path.': '.($stat===false?'missing':sprintf('mode=%04o uid=%d gid=%d readable-by-current-CLI=%s',$stat['mode']&07777,$stat['uid'],$stat['gid'],is_readable($path)?'yes':'no')).PHP_EOL;
}
