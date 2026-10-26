<?php
declare(strict_types=1);

function training_db_check_grants(array $grants,string $identity): void {
    $parts=explode('@',$identity,2);
    if (count($parts)!==2 || $parts[0]!=='pc_forge_training_reader' || !preg_match('/^[a-zA-Z0-9_.:%-]+$/D',$parts[1])) {
        throw new RuntimeException('Unexpected authenticated training identity');
    }
    $identityPatterns=[];
    foreach (['`',"'"] as $quote) {
        $identityPatterns[]=preg_quote($quote.$parts[0].$quote.'@'.$quote.$parts[1].$quote,'/');
    }
    $assignee='(?:'.implode('|',$identityPatterns).')';
    $tables=[];
    foreach ($grants as $grant) {
        if (!is_string($grant)) { throw new RuntimeException('Unexpected grant format'); }
        // USAGE is the connection-only placeholder, not an administrative privilege.
        if (preg_match('/^GRANT USAGE ON \*\.\* TO '.$assignee.'(?: REQUIRE SSL)?$/D',$grant)) { continue; }
        if (preg_match('/^GRANT SELECT ON `pc_forge_training`\.`(users|products)` TO '.$assignee.'$/D',$grant,$match)) {
            $tables[$match[1]]=true; continue;
        }
        // Includes global/dynamic privileges, roles (even inactive), wildcard grants,
        // extra schemas, partial revokes, grant option and unrecognized output.
        throw new RuntimeException('Training grant policy rejected an unexpected privilege or format');
    }
    if (count($tables)!==2) { throw new RuntimeException('Required read-only training table grants are missing'); }
}

function training_db_verify(PDO $pdo,callable $report): void {
    if ($pdo->query('SELECT DATABASE()')->fetchColumn()!=='pc_forge_training') { throw new RuntimeException('Wrong training schema selected'); }
    $status=$pdo->query('SHOW SESSION STATUS')->fetchAll(PDO::FETCH_KEY_PAIR);
    if (empty($status['Ssl_cipher']) || empty($status['Ssl_version'])) { throw new RuntimeException('Encrypted TLS session required'); }
    $report('validated CA/server identity and negotiated TLS');
    $identity=$pdo->query('SELECT CURRENT_USER()')->fetchColumn();
    // No FOR clause: MySQL includes mandatory role assignments for the current user.
    training_db_check_grants($pdo->query('SHOW GRANTS')->fetchAll(PDO::FETCH_COLUMN),(string)$identity);
    $report('exact read-only table grants; no global privileges, roles or grant option');

    // Queries are read-only, fully qualified, bounded, and return only synthetic rows.
    $statement=$pdo->prepare('SELECT name,email,password_hash,role FROM pc_forge_training.users WHERE email=?');
    foreach (['customer'=>['customer@training.test','lab-customer-123'],'admin'=>['admin@training.test','lab-admin-123']] as $role=>[$email,$password]) {
        $statement->execute([$email]);$user=$statement->fetch();
        if (!$user || $user['role']!==$role || !password_verify($password,$user['password_hash'])) { throw new RuntimeException('Synthetic training account contract failed'); }
    }
    $products=$pdo->query('SELECT id,name,price,stock FROM pc_forge_training.products ORDER BY id LIMIT 10')->fetchAll();
    if (!$products) { throw new RuntimeException('Synthetic product contract failed'); }
    $report('prepared synthetic account/password and product read operations');

    foreach (['pc_forge','mens_daydb'] as $schema) {
        try { $pdo->exec('USE `'.$schema.'`'); }
        catch (PDOException $error) {
            if ((int)($error->errorInfo[1]??0)===1044) { $report($schema.' database access denied'); continue; }
            // Missing schema, network errors or missing tables are NOT proof of denial.
            throw new RuntimeException('Protected-schema denial was not proven');
        }
        throw new RuntimeException('Protected-schema access was unexpectedly allowed');
    }
    if ($pdo->query('SELECT DATABASE()')->fetchColumn()!=='pc_forge_training') { throw new RuntimeException('Connection schema changed unexpectedly'); }
}
