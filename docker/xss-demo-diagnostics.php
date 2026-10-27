<?php
declare(strict_types=1);
require_once __DIR__.'/xss-demo-config.php';

function xss_demo_diagnostic_lines(array $env, int $now): array {
    [$enabled,$reason]=xss_demo_configuration_status($env,$now);
    $commit=$env['RENDER_GIT_COMMIT'] ?? '';
    $commit=preg_match('/^[a-fA-F0-9]{40}$/D',$commit) ? $commit : 'unavailable';
    $expiry=$env['XSS_DEMO_EXPIRES_AT'] ?? '';
    $expiryState=!ctype_digit($expiry) ? 'invalid' : ((int)$expiry<=$now ? 'expired' : ((int)$expiry>$now+28800 ? 'over-eight-hours' : 'valid'));
    return [
        'PC Forge XSS diagnostics revision=xss-startup-v3 commit='.$commit,
        'PC Forge XSS settings enabled='.($enabled?'yes':'no').' reason='.$reason,
        'PC Forge XSS flags enable_exact_1='.(($env['XSS_DEMO_ENABLED'] ?? '')==='1'?'yes':'no')
            .' tester_name='.(preg_match('/^[a-zA-Z0-9_-]{1,64}$/D',$env['XSS_DEMO_TESTER_USER'] ?? '')?'valid':'invalid')
            .' bcrypt='.(preg_match('/^\$2[aby]\$(?:0[8-9]|1[0-4])\$[.\/a-zA-Z0-9]{53}$/D',$env['XSS_DEMO_TESTER_BCRYPT'] ?? '')?'valid':'invalid')
            .' expiry='.$expiryState,
    ];
}

function xss_demo_include_status(string $output, int $exitCode): string {
    if ($exitCode!==0) { return 'syntax-or-includes-failed'; }
    // Match an included filename, not arbitrary text containing its name.
    return preg_match('~^\s*\([^\r\n)]*\)\s+/etc/apache2/conf-enabled/pc-forge-xss\.conf\s*$~m',$output)
        ? 'loaded' : 'NOT-LOADED';
}
