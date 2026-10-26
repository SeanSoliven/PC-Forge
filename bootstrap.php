<?php
ini_set('display_errors', '0');
ini_set('log_errors', '1');
ini_set('zend.exception_ignore_args', '1');
set_exception_handler(function (Throwable $error): void {
    log_failure('uncaught request failure', $error);
    while (ob_get_level() > 0) { ob_end_clean(); }
    http_response_code(500);
    header('Content-Type: text/html; charset=UTF-8');
    echo '<!doctype html><html lang="en"><meta charset="utf-8"><title>PC Forge unavailable</title><h1>Something went wrong</h1><p>PC Forge could not complete this request. Please try again later.</p></html>';
});
register_shutdown_function(function (): void {
    $error = error_get_last();
    if ($error && in_array($error['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR], true)) {
        error_log('PC Forge fatal request failure: type=' . $error['type'] . ' file=' . basename($error['file']) . ' line=' . $error['line']);
        while (ob_get_level() > 0) { ob_end_clean(); }
        http_response_code(500);
        echo '<h1>PC Forge is temporarily unavailable</h1><p>Please try again later.</p>';
    }
});
$secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
    || (getenv('RENDER') === 'true' && ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'secure' => $secure, 'httponly' => true, 'samesite' => 'Lax']);
if (!session_start()) { throw new RuntimeException('Session initialization failed'); }
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: strict-origin-when-cross-origin');
header('Cache-Control: no-store');

require_once __DIR__ . '/config/db.php';
// Buffer page rendering for safe error pages only after sessions and headers work.
ob_start();

function log_failure(string $context, Throwable $error): void {
    // Messages and exception arguments can contain SQL, credentials, or user input.
    $code = $error instanceof PDOException ? ($error->errorInfo[0] ?? 'unknown') : $error->getCode();
    $driver = $error instanceof PDOException ? ($error->errorInfo[1] ?? 'unknown') : 'none';
    error_log(sprintf('PC Forge %s: type=%s code=%s driver=%s route=%s file=%s line=%d', $context, get_class($error), $code, $driver, basename($_SERVER['SCRIPT_NAME'] ?? 'cli'), basename($error->getFile()), $error->getLine()));
}
function request_error(Throwable $error, string $context): string {
    if ($error instanceof InvalidArgumentException) {
        http_response_code(422);
        return $error->getMessage();
    }
    log_failure($context, $error);
    http_response_code(500);
    return 'This request could not be completed. Please try again later.';
}
function input(array $source, string $key): string {
    $value = $source[$key] ?? '';
    if (!is_string($value)) { throw new InvalidArgumentException('Invalid form input.'); }
    return $value;
}
function current_user() { return $_SESSION['user'] ?? null; }
function require_login(): void { if (!current_user()) { redirect('login.php'); } }
function require_admin(): void {
    if (!current_user()) { redirect('../login.php'); }
    $statement = db()->prepare('SELECT role FROM users WHERE id=?');
    $statement->execute([current_user()['id']]);
    if ($statement->fetchColumn() !== 'admin') {
        http_response_code(403);
        exit('Admin access required');
    }
    $_SESSION['user']['role'] = 'admin';
}
function cart_count(): int { return array_sum(array_map('intval', $_SESSION['cart'] ?? [])); }
