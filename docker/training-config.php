<?php
function training_apache_config(string $token): string {
return <<<APACHE
ProxyRequests Off
ProxyPassMatch "^/training$" "!"
RedirectMatch 302 "^/training$" "/training/"
ProxyPass "/training/" "http://127.0.0.1:9081/" connectiontimeout=2 timeout=10
ProxyPassReverse "/training/" "http://127.0.0.1:9081/"
<Location "/training/">
    AuthType Basic
    AuthName "Authorized instruction"
    AuthBasicProvider file
    AuthUserFile "/run/pc-forge-training-auth/instructors"
    <RequireAll>
        Require valid-user
        Require expr "req('X-Forwarded-Proto') == 'https'"
    </RequireAll>
    RequestHeader unset Cookie
    RequestHeader unset Authorization
    RequestHeader unset Proxy-Authorization
    RequestHeader unset X-Forwarded-For
    RequestHeader unset X-Forwarded-Host
    RequestHeader set X-PC-Forge-Training "$token"
    Header unset Set-Cookie
    Header always unset Set-Cookie
    Header always set Cache-Control "no-store"
    Header always set Content-Security-Policy "default-src 'self'; script-src 'none'; connect-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
    Header always set X-Content-Type-Options "nosniff"
</Location>
APACHE;
}
