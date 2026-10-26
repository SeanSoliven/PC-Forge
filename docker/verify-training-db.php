<?php
declare(strict_types=1);
ini_set('display_errors','0');
ini_set('zend.exception_ignore_args','1');
if (PHP_SAPI!=='cli') { http_response_code(404); exit; }
if ($argc!==2 || $argv[1]!=='--verify') {
    fwrite(STDERR,"Usage: php verify-training-db.php --verify\nNo connection is made without the explicit flag.\n"); exit(2);
}
require __DIR__.'/training-db-config.php';
require __DIR__.'/training-db-policy.php';
$phase='configuration';
try {
    $config=training_db_config(getenv());
    $phase='TLS connection';
    $pdo=training_db_connect($config);
    $phase='privileges and read-only contract';
    training_db_verify($pdo,function(string $name): void { echo 'PASS: '.$name.PHP_EOL; });
    echo "VERIFIED for this connection and time only. No training mode enabled; no data/grants changed.\n";
} catch (Throwable $error) {
    $state=$error instanceof PDOException ? ($error->errorInfo[0]??'unknown') : 'policy';
    $code=$error instanceof PDOException ? ($error->errorInfo[1]??0) : 0;
    // Never emit driver messages, grants, usernames, hostnames, passwords or traces.
    fwrite(STDERR,'FAIL: training DB verification phase='.$phase.' SQLSTATE='.$state.' driver_code='.$code.PHP_EOL);
    exit(1);
}
