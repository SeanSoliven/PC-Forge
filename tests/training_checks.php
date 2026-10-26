<?php
declare(strict_types=1);
require __DIR__.'/../config/login_limit.php';
require __DIR__.'/../docker/training-config.php';
function verify_check(bool $ok,string $name): void {
    if (!$ok) { fwrite(STDERR,"FAIL: $name\n"); exit(1); }
    echo "PASS: $name\n";
}
$directory=sys_get_temp_dir().'/pc-forge-limit-test-'.bin2hex(random_bytes(8));
mkdir($directory,0700); putenv('PCFORGE_RATE_DIR='.$directory);
try {
    for ($i=0;$i<15;$i++) { verify_check(login_budget('synthetic@example.test')===0,'under account budget'); }
    verify_check(login_budget('synthetic@example.test')>0,'account limit is independent of proxy IP/session');
    $states=json_decode(file_get_contents($directory.'/budgets.json'),true);
    foreach ($states as &$state) { $state['start']=time()-301; } unset($state);
    file_put_contents($directory.'/budgets.json',json_encode($states));
    verify_check(login_budget('synthetic@example.test')===0,'budget expiration');
    $allowed=true;
    for ($i=0;$i<650;$i++) { $allowed=$allowed && login_budget('shared-proxy-'.$i.'@example.test')===0; }
    verify_check($allowed,'650 unrelated accounts never share a proxy-IP budget');
    file_put_contents($directory.'/budgets.json','invalid json');
    $failed=false;
    try { login_budget('x'); } catch (Throwable $error) { $failed=true; }
    verify_check($failed,'corrupt storage fails closed');
} finally {
    unlink($directory.'/budgets.json'); rmdir($directory); putenv('PCFORGE_RATE_DIR');
}
$config=training_apache_config(str_repeat('a',64));
foreach (['Require valid-user','RequestHeader unset Cookie','RequestHeader unset Authorization',
          'Header always unset Set-Cookie','http://127.0.0.1:9081/','script-src \'none\''] as $required) {
    verify_check(str_contains($config,$required),'proxy policy includes '.$required);
}
verify_check(!str_contains(file_get_contents(__DIR__.'/../layout.php'),'/training'),'no public navigation link');
verify_check(!str_contains(file_get_contents(__DIR__.'/../training-src/public/index.php'),'new PDO'),'preview has no database connection');
foreach (['setup.sql','reset.sql'] as $name) {
    $sql=file_get_contents(__DIR__.'/../training-src/database/'.$name);
    preg_match_all('/\b(?:CREATE TABLE|INSERT INTO|UPDATE)\s+([a-zA-Z0-9_.]+)/i',$sql,$matches);
    verify_check(count($matches[1])>0 && count(array_filter($matches[1],fn($table)=>!str_starts_with($table,'pc_forge_training.')))===0,$name.' qualifies every modified table in the synthetic schema');
}
