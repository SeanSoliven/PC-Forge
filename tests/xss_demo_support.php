<?php
declare(strict_types=1);

// Never load production bootstrap, authentication, sessions or database helpers.
if (PHP_SAPI !== 'cli-server' || !defined('PCFORGE_XSS_DEMO_ROUTED')
    || getenv('PCFORGE_XSS_DEMO_ENABLED') !== '1'
    || ($_SERVER['SERVER_NAME'] ?? '') !== '127.0.0.1'
    || !in_array($_SERVER['REMOTE_ADDR'] ?? '', ['127.0.0.1', '::1'], true)
    || !preg_match('/^(?:127\.0\.0\.1|localhost):[0-9]+$/D', $_SERVER['HTTP_HOST'] ?? '')) {
    http_response_code(403);
    exit('Local demonstration launcher required.');
}
header('Content-Type: text/html; charset=UTF-8');
header('Cache-Control: no-store');
header('Referrer-Policy: no-referrer');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
    header('Allow: GET');
    http_response_code(405);
    exit('GET only.');
}

function demo_escape(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function demo_query(): string {
    $value = $_GET['q'] ?? '';
    if (!is_string($value) || strlen($value) > 512) {
        http_response_code(400);
        exit('Use a synthetic search string of at most 512 bytes.');
    }
    return $value;
}

function demo_head(bool $fixed): void {
    // Only the intentionally vulnerable page permits inline execution.
    $scripts = $fixed ? "'none'" : "'unsafe-inline'";
    header("Content-Security-Policy: default-src 'none'; script-src $scripts; style-src 'self'; connect-src 'none'; img-src 'none'; object-src 'none'; frame-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'");
    $label = $fixed ? 'Fixed encoding' : 'Intentionally vulnerable';
    echo '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PC Forge · '.$label.'</title><link rel="stylesheet" href="/style.css"></head><body>';
    echo '<header class="top"><a class="brand" href="/xss_vulnerable_demo.php">PC<span>FORGE</span></a><nav><a href="/xss_vulnerable_demo.php">Vulnerable</a><a href="/xss_fixed_demo.php">Fixed</a></nav></header><main class="wrap">';
    echo '<section class="hero"><span class="accent">SYNTHETIC SEARCH ONLY</span><h1>'.$label.'</h1><p>Isolated loopback demonstration. No accounts, cookies, database, orders or production traffic.</p></section>';
}

function demo_foot(string $query): void {
    echo '<h2>Shop components</h2><div class="grid">';
    foreach (['Synthetic Ryzen CPU', 'Synthetic GPU', 'Synthetic DDR5 Memory'] as $product) {
        if ($query !== '' && stripos($product, $query) === false) { continue; }
        echo '<article class="product"><p class="muted">Synthetic component</p><h3>'.demo_escape($product).'</h3><p>Presentation data only</p></article>';
    }
    echo '</div><p>Use only the documented alert proof of concept. Stop the PHP server after collecting evidence.</p></main><footer class="footer">PC Forge · Isolated academic example</footer></body></html>';
}
