<?php
require __DIR__.'/bootstrap.php';
if ($_SERVER['REQUEST_METHOD']!=='POST') {
    http_response_code(405);
    header('Allow: POST');
    exit('Use the Logout button to sign out.');
}
try { check_csrf(); } catch (InvalidArgumentException $e) { http_response_code(403); exit('Invalid request token. Reload the page and try again.'); }
$_SESSION=[];
$params=session_get_cookie_params();
setcookie(session_name(), '', ['expires'=>time()-3600, 'path'=>$params['path'], 'domain'=>$params['domain'], 'secure'=>$params['secure'], 'httponly'=>true, 'samesite'=>'Lax']);
session_destroy();
redirect('index.php');
