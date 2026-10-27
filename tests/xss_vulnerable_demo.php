<?php
declare(strict_types=1);
require_once __DIR__.'/xss_demo_support.php';
$query = demo_query();
demo_head(false);
?>
<h2>Search components</h2>
<form class="filters" method="get" action="/xss_vulnerable_demo.php">
    <!-- UNSAFE ATTRIBUTE SINK: a matching quote can introduce an event handler. -->
    <input type="search" name="q" value="<?= $query ?>" placeholder="Search computer parts...">
    <button class="btn">Search</button>
</form>
<!-- UNSAFE TEXT SINK: submitted tags become HTML, including inline scripts. -->
<p id="search-summary">Search results for: <?= $query ?></p>
<?php demo_foot($query); ?>
