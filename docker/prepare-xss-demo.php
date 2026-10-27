<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require __DIR__.'/xss-demo-config.php';
try {
    [$enabled,$reason] = xss_demo_configuration_status(getenv(),time());
    if ($enabled) {
        $user = getenv('XSS_DEMO_TESTER_USER') ?: '';
        $hash = getenv('XSS_DEMO_TESTER_BCRYPT') ?: '';
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
    echo 'PC Forge: XSS demo route '.($enabled?'authenticated':'denied').' reason='.$reason.' target=/opt/pc-forge-xss'.PHP_EOL;
} catch (Throwable $e) {
    // Invalid/expired optional demo settings must not take down the storefront.
    $deny=xss_demo_apache_config(false)."\n";
    $path='/etc/apache2/conf-enabled/pc-forge-xss.conf';
    if (file_put_contents($path,$deny)!==strlen($deny) || !chown($path,'root') || !chmod($path,0640)) {
        fwrite(STDERR,"PC Forge startup error: cannot enforce disabled XSS demo configuration.\n"); exit(1);
    }
    fwrite(STDERR,"PC Forge: XSS demo route denied reason=runtime-file-preparation-failed target=/opt/pc-forge-xss; storefront continues.\n");
}
