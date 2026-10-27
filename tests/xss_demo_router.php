<?php
declare(strict_types=1);
define('PCFORGE_XSS_DEMO_ROUTED', true);
require __DIR__.'/xss_demo_support.php';
$path = parse_url($_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH);
if ($path === '/style.css') {
    header('Content-Type: text/css; charset=UTF-8');
    readfile(__DIR__.'/../assets/style.css');
    exit;
}
$routes = ['/xss_vulnerable_demo.php'=>'xss_vulnerable_demo.php', '/xss_fixed_demo.php'=>'xss_fixed_demo.php'];
if (!isset($routes[$path])) {
    http_response_code(404);
    exit('Not found. Only the two synthetic demonstration pages are available.');
}
// Pages reuse the already-checked support file through require_once.
require __DIR__.'/'.$routes[$path];
