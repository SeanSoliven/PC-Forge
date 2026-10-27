<?php
declare(strict_types=1);
// No top-level output: direct requests cannot render a demonstration.
function xss_demo_value(array $input): array {
    $reflected="<script>alert('XSS Demonstration Successful')</script>";
    $attribute="\" onclick=\"alert('XSS Demonstration Successful')\" data-demo=\"";
    $mode=$input['version'] ?? 'fixed';
    $value=$input['q'] ?? '';
    if (!is_string($mode) || !in_array($mode,['vulnerable','fixed'],true) || !is_string($value)
        || !in_array($value,['','Synthetic','Ryzen','<b>XSS Test</b>',$reflected,$attribute],true)
        || array_diff(array_keys($input),['version','q'])) { throw new InvalidArgumentException('Predefined synthetic inputs only'); }
    return [$mode,$value];
}
function xss_html(string $value): string { return htmlspecialchars($value,ENT_QUOTES | ENT_SUBSTITUTE,'UTF-8'); }
function xss_render(array $input): void {
    try { [$mode,$value]=xss_demo_value($input); }
    catch (InvalidArgumentException $e) { http_response_code(400); echo 'Predefined synthetic inputs only.'; return; }
    $fixed=$mode==='fixed';
    $scripts=$fixed ? "'none'" : "'unsafe-inline'";
    // Opaque sandbox origin: scripts cannot read storefront storage, cookies or DOM.
    header("Content-Security-Policy: sandbox allow-scripts allow-modals; default-src 'none'; script-src $scripts; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; frame-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'");
    $display=$fixed ? xss_html($value) : $value; // Intentionally raw ONLY after exact payload allowlist.
    $css=file_get_contents(__DIR__.'/style.css');
    echo '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>PC Forge synthetic XSS exercise</title><style>'.$css.'</style><header class="top"><span class="brand">PC<span>FORGE</span></span></header><main class="wrap"><section class="hero"><h1>'.($fixed?'Fixed':'Vulnerable').' synthetic search</h1><p>Authorized, time-limited exercise. Fixed alert payloads only; no production accounts or data.</p></section>';
    echo '<input type="search" name="q" value="'.$display.'" placeholder="Synthetic search"><p id="search-summary">Search results for: '.$display.'</p>';
    echo '<p>Choose a predefined input. Attribute case: click the search input. No form submission or arbitrary payloads.</p><nav>';
    $cases=['Normal'=>'Synthetic','Reflected'=>"<script>alert('XSS Demonstration Successful')</script>",'Attribute'=>"\" onclick=\"alert('XSS Demonstration Successful')\" data-demo=\"",'Bold'=>'<b>XSS Test</b>'];
    foreach (['vulnerable','fixed'] as $version) { foreach ($cases as $label=>$query) {
        echo '<a class="btn" href="/xss-demo/?'.xss_html(http_build_query(['version'=>$version,'q'=>$query])).'">'.xss_html($version.' '.$label).'</a>';
    }}
    echo '</nav><h2>Shop components</h2><div class="grid">';
    foreach (['Synthetic Ryzen CPU','Synthetic GPU','Synthetic DDR5 Memory'] as $product) {
        if ($value!=='' && stripos($product,$value)===false) { continue; }
        echo '<article class="product"><h3>'.xss_html($product).'</h3><p>Synthetic component</p></article>';
    }
    echo '</div></main></html>';
}
