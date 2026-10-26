<?php
declare(strict_types=1);
function training_write(string $path,string $content,string $group,int $mode): void {
    if (file_put_contents($path,$content)!==strlen($content) || !chown($path,'root') || !chgrp($path,$group) || !chmod($path,$mode)) {
        fwrite(STDERR,"PC Forge startup error: cannot prepare private training configuration.\n"); exit(1);
    }
}
// Root startup only. This provisions a SAFE preview, never vulnerable execution.
$configuration = '/etc/apache2/conf-enabled/pc-forge-training.conf';
$disabled = "<LocationMatch \"^/training(?:/|$)\">\n    Require all denied\n</LocationMatch>\n";
if (getenv('TRAINING_PREVIEW_ENABLED') !== '1') {
    training_write($configuration,$disabled,'www-data',0640);
    exit;
}
$user = getenv('TRAINING_INSTRUCTOR_USER') ?: '';
$hash = getenv('TRAINING_INSTRUCTOR_BCRYPT') ?: '';
if (!preg_match('/^[a-zA-Z0-9_-]{1,64}$/D', $user)
    || !preg_match('/^\$2[aby]\$(?:0[4-9]|1[0-4])\$[.\/a-zA-Z0-9]{53}$/D', $hash)) {
    fwrite(STDERR, "PC Forge startup error: preview requires an instructor username and valid bcrypt hash (cost 4–14).\n");
    exit(1);
}
foreach (['/run/pc-forge-training'=>['pc-training',0750], '/run/pc-forge-training-auth'=>['www-data',0750]] as $path=>$settings) {
    if (!is_dir($path) && !mkdir($path, 0750, true)) { exit(1); }
    chown($path,'root'); chgrp($path,$settings[0]); chmod($path,$settings[1]);
}
$sessions='/run/pc-forge-training/sessions';
if (!is_dir($sessions) && !mkdir($sessions,0700)) { exit(1); }
chown($sessions,'pc-training'); chgrp($sessions,'pc-training'); chmod($sessions,0700);
$auth='/run/pc-forge-training-auth/instructors';
training_write($auth,$user.':'.$hash."\n",'www-data',0640);
$token=bin2hex(random_bytes(32));
training_write('/run/pc-forge-training/proxy-token',$token,'pc-training',0640);
require __DIR__.'/training-config.php';
$enabled=training_apache_config($token);
training_write($configuration,$enabled."\n",'www-data',0640);
