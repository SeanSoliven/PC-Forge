<?php
declare(strict_types=1);
require_once __DIR__.'/xss_demo_support.php';
$query = demo_query();
demo_head(true);
?>
<h2>Search components</h2>
<form class="filters" method="get" action="/xss_fixed_demo.php">
    <!-- FIXED ATTRIBUTE SINK: encode both quote types inside a quoted value. -->
    <input type="search" name="q" value="<?= demo_escape($query) ?>" placeholder="Search computer parts...">
    <button class="btn">Search</button>
</form>
<!-- FIXED TEXT SINK: angle brackets and ampersands remain ordinary text. -->
<p id="search-summary">Search results for: <?= demo_escape($query) ?></p>
<?php demo_foot($query); ?>
