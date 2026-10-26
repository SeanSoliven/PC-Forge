<?php
declare(strict_types=1);
require __DIR__.'/../docker/training-db-config.php';
require __DIR__.'/../docker/training-db-policy.php';
function db_check(bool $ok,string $name): void { if (!$ok) { fwrite(STDERR,"FAIL: $name\n"); exit(1); } echo "PASS: $name\n"; }
function db_rejected(callable $operation): bool { try { $operation(); return false; } catch (RuntimeException $error) { return true; } }
$identity='pc_forge_training_reader@%';
$to='`pc_forge_training_reader`@`%`';
$valid=['GRANT USAGE ON *.* TO '.$to,'GRANT SELECT ON `pc_forge_training`.`users` TO '.$to,'GRANT SELECT ON `pc_forge_training`.`products` TO '.$to];
training_db_check_grants($valid,$identity);db_check(true,'minimal training SELECT grants accepted');
foreach (['GRANT SELECT ON *.* TO '.$to,'GRANT FILE ON *.* TO '.$to,
          'GRANT CREATE USER ON *.* TO '.$to,'GRANT ROLE_ADMIN ON *.* TO '.$to,
          'GRANT SELECT ON `pc_forge`.* TO '.$to,'GRANT SELECT ON `mens_daydb`.* TO '.$to,
          'GRANT SELECT ON `pc_forge_training`.* TO '.$to,
          'GRANT UPDATE ON `pc_forge_training`.`users` TO '.$to,
          'GRANT SELECT ON `pc_forge_training`.`users` TO '.$to.' WITH GRANT OPTION',
          'GRANT `privileged_role`@`%` TO '.$to] as $bad) {
    db_check(db_rejected(fn()=>training_db_check_grants([...$valid,$bad],$identity)),'unsafe/global/role/extra-schema grant rejected');
}
db_check(db_rejected(fn()=>training_db_check_grants(array_slice($valid,0,2),$identity)),'missing required table grant rejected');
db_check(db_rejected(fn()=>training_db_check_grants($valid,'avnadmin@%')),'wrong authenticated account rejected');
$config=['TRAINING_DB_HOST'=>'never-connect.invalid','TRAINING_DB_PORT'=>'3306','TRAINING_DB_NAME'=>'pc_forge_training',
    'TRAINING_DB_USER'=>'pc_forge_training_reader','TRAINING_DB_PASSWORD'=>'synthetic-reader-only',
    'TRAINING_DB_SSL_CA'=>__DIR__.'/missing-training-ca.pem'];
db_check(count(training_db_config($config))===6,'training-only variables accepted');
foreach (['pc_forge','mens_daydb'] as $name) {
    db_check(db_rejected(fn()=>training_db_config(array_replace($config,['TRAINING_DB_NAME'=>$name]))),'protected DB name rejected before connecting');
}
db_check(db_rejected(fn()=>training_db_config(array_replace($config,['TRAINING_DB_HOST'=>'localhost;dbname=pc_forge']))),'DSN injection rejected');
db_check(db_rejected(fn()=>training_db_config(array_replace($config,['TRAINING_DB_PORT'=>'0']))),'invalid port rejected');
db_check(db_rejected(fn()=>training_db_config(array_replace($config,['DB_PASSWORD'=>'synthetic-reader-only']))),'production password reuse rejected');
db_check(db_rejected(fn()=>training_db_config(['DB_HOST'=>'production.invalid'])),'no fallback to production variables');
db_check(db_rejected(fn()=>training_db_connect($config)),'missing CA rejected before any network connection');
$config['TRAINING_DB_SSL_CA']=__DIR__.'/../Dockerfile';
db_check(db_rejected(fn()=>training_db_connect($config)),'invalid PEM rejected before any network connection');
