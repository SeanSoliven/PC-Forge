<?php
declare(strict_types=1);
// Root-only, disposable Docker fixture. Read from stdin by container-isolation.sh.
function check_probe(bool $ok,string $name): void {
    if (!$ok) { fwrite(STDERR,"FAIL: $name\n"); exit(1); }
    echo "PASS: $name\n";
}
$production=posix_getpwnam('www-data');$training=posix_getpwnam('pc-training');
check_probe($production!==false && $training!==false && $production['uid']!==$training['uid'] && $training['uid']!==0,'distinct non-root production/training users');
check_probe((fileperms('/run/pc-forge/ca.pem') & 0777)===0640
    && (fileperms('/run/pc-forge') & 0777)===0755
    && fileowner('/run/pc-forge/ca.pem')===0
    && filegroup('/run/pc-forge/ca.pem')===posix_getgrnam('www-data')['gid'],'production CA ownership/modes preserved');
check_probe(ini_get('session.save_path')==='/run/pc-forge-production-sessions','production PHP uses its private session directory');
$apacheWorker=false;$trainingWorker=false;
foreach (glob('/proc/[0-9]*/status') ?: [] as $path) {
    $status=@file_get_contents($path);$command=@file_get_contents(dirname($path).'/cmdline');
    if (!$status || $command===false || !preg_match('/^Uid:\s+(\d+)/m',$status,$match)) { continue; }
    $uid=(int)$match[1];
    if ($uid===$production['uid'] && str_contains($status,"Name:\tapache2")) { $apacheWorker=true; }
    if ($uid===$training['uid'] && str_contains($command,'127.0.0.1:9081')) {
        $trainingWorker=true;
        // Linux ptrace restrictions can deny even root this environ read. Never
        // turn an unreadable file into an empty environment and report a pass.
        // The actual backend validates its environment in training-router.php;
        // the authenticated HTTP 200 assertion exercises that fail-closed guard.
    }
}
check_probe($apacheWorker && $trainingWorker,'live Apache and preview workers have the expected distinct UIDs');
check_probe(getenv('DB_PASSWORD')==='synthetic-production-secret','production secret fixture exists');
check_probe(getenv('TRAINING_DB_USER')==='synthetic-training-reader'
    && getenv('TRAINING_DB_USER')!==getenv('DB_USER')
    && getenv('TRAINING_DB_PASSWORD')!==getenv('DB_PASSWORD'),'synthetic training/production credential markers differ (not a real grant test)');
$id='synthetictrainingadminfixture123456';
$session='user|'.serialize(['id'=>999999,'name'=>'Synthetic Training Admin','role'=>'admin','email'=>'fixture@training.test']);
$trainingFile='/run/pc-forge-training/sessions/sess_'.$id;
file_put_contents($trainingFile,$session);chown($trainingFile,'pc-training');chgrp($trainingFile,'pc-training');chmod($trainingFile,0600);
$productionFile='/run/pc-forge-production-sessions/sess_productionfixture123456';
file_put_contents($productionFile,'fixture|s:9:"synthetic";');chown($productionFile,'www-data');chgrp($productionFile,'www-data');chmod($productionFile,0600);
check_probe(fileowner($productionFile)===$production['uid'] && fileowner($trainingFile)===$training['uid'],'session fixture ownership is separate');
