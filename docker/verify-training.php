<?php
declare(strict_types=1);
// Run with env -i as pc-training, without open_basedir masking OS permissions.
if (!function_exists('posix_geteuid') || posix_geteuid() === 0 || posix_getpwuid(posix_geteuid())['name'] !== 'pc-training') {
    fwrite(STDERR,"Training isolation check failed: wrong UID.\n"); exit(1);
}
$productionGroup=posix_getgrnam('www-data');
if (!$productionGroup || in_array($productionGroup['gid'],posix_getgroups(),true)) {
    fwrite(STDERR,"Training isolation check failed: production group membership.\n"); exit(1);
}
$allowedEnvironment=['PATH','HOME','SHELL','USER','LOGNAME'];
foreach (array_keys(getenv()) as $name) {
    if (!in_array($name,$allowedEnvironment,true)) { fwrite(STDERR,"Training isolation check failed: unexpected inherited environment.\n"); exit(1); }
}
foreach (['DB_HOST','DB_PORT','DB_NAME','DB_USER','DB_PASSWORD','DB_SSL_CA','TRAINING_INSTRUCTOR_BCRYPT','TRAINING_INSTRUCTOR_USER','RENDER'] as $name) {
    if (getenv($name)!==false) { fwrite(STDERR,"Training isolation check failed: inherited environment.\n"); exit(1); }
}
foreach (['/var/www/html/config/db.php','/etc/secrets/ca.pem','/run/pc-forge/ca.pem',
          '/run/pc-forge-production-sessions','/run/pc-forge-login',
          '/run/pc-forge-training-auth/instructors','/proc/1/environ'] as $path) {
    clearstatcache();
    if (is_readable($path) || @file_get_contents($path)!==false) {
        fwrite(STDERR,"Training isolation check failed: forbidden resource readable.\n"); exit(1);
    }
}
foreach (glob('/etc/secrets/*') ?: [] as $path) {
    if (is_readable($path)) { fwrite(STDERR,"Training isolation check failed: mounted secret readable.\n"); exit(1); }
}
foreach (glob('/proc/[0-9]*/environ') ?: [] as $path) {
    $owner=@fileowner(dirname($path));
    if ($owner!==false && $owner!==posix_geteuid() && @file_get_contents($path)!==false) {
        fwrite(STDERR,"Training isolation check failed: foreign process environment readable.\n"); exit(1);
    }
}
if (!is_readable('/opt/pc-forge-training/index.php') || !is_writable('/run/pc-forge-training/sessions')) {
    fwrite(STDERR,"Training isolation check failed: preview resources unavailable.\n"); exit(1);
}
echo "PC Forge: training UID/environment/filesystem probes passed; vulnerable authentication remains absent.\n";
