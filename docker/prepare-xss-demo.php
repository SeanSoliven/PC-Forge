<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require __DIR__.'/xss-demo-config.php';
try {
    $enabled = getenv('XSS_DEMO_ENABLED') === '1';
    if ($enabled) {
        $user = getenv('XSS_DEMO_TESTER_USER') ?: '';
        $hash = getenv('XSS_DEMO_TESTER_BCRYPT') ?: '';
        $expiry = getenv('XSS_DEMO_EXPIRES_AT') ?: '';
        if (!preg_match('/^[a-zA-Z0-9_-]{1,64}$/D', $user)
            || !preg_match('/^\$2[aby]\$(?:0[8-9]|1[0-4])\$[.\/a-zA-Z0-9]{53}$/D', $hash)
            || !ctype_digit($expiry) || (int)$expiry <= time() || (int)$expiry > time()+28800) {
            throw new RuntimeException('Invalid enabled configuration');
        }
        $dir = '/run/pc-forge-xss-auth';
        if (!is_dir($dir) && !mkdir($dir,0750,true)) { throw new RuntimeException('Private directory'); }
        if (!chown($dir,'root') || !chgrp($dir,'www-data') || !chmod($dir,0750)) { throw new RuntimeException('Directory ownership'); }
        $auth = $dir.'/testers';
        $contents = $user.':'.$hash."\n";
        if (file_put_contents($auth,$contents)!==strlen($contents) || !chown($auth,'root') || !chgrp($auth,'www-data') || !chmod($auth,0640)) {
            throw new RuntimeException('Private auth file');
        }
    }
    $file='/etc/apache2/conf-enabled/pc-forge-xss.conf';
    $content=xss_demo_apache_config($enabled)."\n";
    if (file_put_contents($file,$content)!==strlen($content) || !chown($file,'root') || !chmod($file,0640)) { throw new RuntimeException('Apache config'); }
} catch (Throwable $e) {
    // Invalid/expired optional demo settings must not take down the storefront.
    $deny=xss_demo_apache_config(false)."\n";
    $path='/etc/apache2/conf-enabled/pc-forge-xss.conf';
    if (file_put_contents($path,$deny)!==strlen($deny) || !chown($path,'root') || !chmod($path,0640)) {
        fwrite(STDERR,"PC Forge startup error: cannot enforce disabled XSS demo configuration.\n"); exit(1);
    }
    fwrite(STDERR,"PC Forge: XSS demo settings invalid or expired; route disabled, storefront continues.\n");
}
