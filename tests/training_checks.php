<?php
declare(strict_types=1);
require __DIR__.'/../docker/training-config.php';
function verify_check(bool $ok,string $name): void {
    if (!$ok) { fwrite(STDERR,"FAIL: $name\n"); exit(1); }
    echo "PASS: $name\n";
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
