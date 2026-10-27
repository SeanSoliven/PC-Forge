<?php
declare(strict_types=1);
// Fixed allowlisted teaching content only. Never import production bootstrap/DB/session code.
ini_set('display_errors','0');
header('Cache-Control: no-store');
header('Content-Type: text/html; charset=UTF-8');
$reason=null;
if (PHP_SAPI !== 'apache2handler') { $reason='wrong-sapi'; }
elseif (getenv('XSS_DEMO_ENABLED') !== '1') { $reason='not-enabled'; }
elseif (empty($_SERVER['REMOTE_USER'])) { $reason='missing-authenticated-user'; }
elseif (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') !== 'https') { $reason='forwarded-https-required'; }
elseif (!ctype_digit(getenv('XSS_DEMO_EXPIRES_AT') ?: '')) { $reason='invalid-expiry'; }
elseif (time() >= (int)getenv('XSS_DEMO_EXPIRES_AT')) { $reason='expired'; }
if ($reason!==null) {
    if (PHP_SAPI==='apache2handler') { error_log('PC Forge XSS request denied layer=php reason='.$reason); }
    http_response_code(403); exit('Demonstration unavailable.');
}
if ($_SERVER['REQUEST_METHOD'] !== 'GET') { header('Allow: GET'); http_response_code(405); exit; }
require __DIR__.'/render.php';
xss_render($_GET);
