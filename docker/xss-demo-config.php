<?php
declare(strict_types=1);
function xss_demo_configuration_status(array $env, int $now): array {
    if (($env['XSS_DEMO_ENABLED'] ?? '') !== '1') { return [false,'not-enabled']; }
    if (!preg_match('/^[a-zA-Z0-9_-]{1,64}$/D', $env['XSS_DEMO_TESTER_USER'] ?? '')) { return [false,'invalid-tester-name']; }
    if (!preg_match('/^\$2[aby]\$(?:0[8-9]|1[0-4])\$[.\/a-zA-Z0-9]{53}$/D', $env['XSS_DEMO_TESTER_BCRYPT'] ?? '')) { return [false,'invalid-bcrypt']; }
    $expiry=$env['XSS_DEMO_EXPIRES_AT'] ?? '';
    if (!ctype_digit($expiry)) { return [false,'invalid-expiry']; }
    if ((int)$expiry <= $now) { return [false,'expired']; }
    if ((int)$expiry > $now+28800) { return [false,'expiry-over-eight-hours']; }
    return [true,'enabled'];
}
function xss_demo_apache_config(bool $enabled): string {
    if (!$enabled) {
        // Retain the real filesystem mapping even while denied. Never fall back
        // to /var/www/html/xss-demo, which obscures why the optional route is off.
        return "Alias \"/xss-demo/\" \"/opt/pc-forge-xss/\"\n<Directory \"/opt/pc-forge-xss\">\n    AllowOverride None\n    Require all denied\n</Directory>\n<LocationMatch \"^/xss-demo(?:/|$)\">\n    Require all denied\n</LocationMatch>\n";
    }
    return <<<'APACHE'
Alias "/xss-demo/" "/opt/pc-forge-xss/"
<Directory "/opt/pc-forge-xss">
    AllowOverride None
    Options -Indexes -ExecCGI
    DirectoryIndex index.php
    AuthMerging Off
    AuthType Basic
    AuthName "PC Forge authorized synthetic XSS exercise"
    AuthBasicProvider file
    AuthUserFile "/run/pc-forge-xss-auth/testers"
    <RequireAll>
        Require valid-user
        Require expr "req('X-Forwarded-Proto') == 'https'"
    </RequireAll>
    RequestHeader unset Cookie
    RequestHeader unset Proxy-Authorization
    Header unset Set-Cookie
    Header always unset Set-Cookie
    Header always set Cache-Control "no-store"
    Header always set Referrer-Policy "no-referrer"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"
</Directory>
<LocationMatch "^/xss-demo$">
    Require all denied
</LocationMatch>
APACHE;
}
