<?php
declare(strict_types=1);
$token=@file_get_contents('/run/pc-forge-training/proxy-token');
if (PHP_SAPI!=='cli-server' || !is_string($token) || strlen($token)!==64
    || !in_array($_SERVER['REMOTE_ADDR']??'', ['127.0.0.1','::1'], true)
    || !hash_equals($token,$_SERVER['HTTP_X_PC_FORGE_TRAINING']??'')
    || isset($_SERVER['HTTP_COOKIE']) || isset($_SERVER['HTTP_AUTHORIZATION'])) {
    http_response_code(403); exit('Access denied');
}
header('Cache-Control: no-store');
header("Content-Security-Policy: default-src 'self'; script-src 'none'; connect-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'");
$path=parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH);
if ($path==='/assets/style.css') { header('Content-Type: text/css'); readfile('/opt/pc-forge-training/assets/style.css'); return; }
if (in_array($path,['/','/index.php','/login.php'],true)) { require '/opt/pc-forge-training/index.php'; return; }
http_response_code(404); echo 'Not found';
