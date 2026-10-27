<?php
declare(strict_types=1);
function xss_demo_apache_config(bool $enabled): string {
    if (!$enabled) { return "<LocationMatch \"^/xss-demo(?:/|$)\">\nRequire all denied\n</LocationMatch>\n"; }
    return <<<'APACHE'
Alias "/xss-demo/" "/opt/pc-forge-xss/"
<Directory "/opt/pc-forge-xss">
    AllowOverride None
    Options -Indexes -ExecCGI
    DirectoryIndex index.php
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
