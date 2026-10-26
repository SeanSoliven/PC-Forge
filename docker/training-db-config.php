<?php
declare(strict_types=1);

// Pure configuration validation. Never falls back to production DB_* values.
function training_db_config(array $environment): array {
    $required=['TRAINING_DB_HOST','TRAINING_DB_PORT','TRAINING_DB_NAME','TRAINING_DB_USER','TRAINING_DB_PASSWORD','TRAINING_DB_SSL_CA'];
    foreach ($required as $name) {
        if (!isset($environment[$name]) || !is_string($environment[$name]) || $environment[$name]==='') {
            throw new RuntimeException('Missing training-only database configuration');
        }
    }
    if ($environment['TRAINING_DB_NAME']!=='pc_forge_training'
        || $environment['TRAINING_DB_USER']!=='pc_forge_training_reader'
        || !preg_match('/^[a-zA-Z0-9_.:-]+$/D',$environment['TRAINING_DB_HOST'])
        || !ctype_digit($environment['TRAINING_DB_PORT'])
        || (int)$environment['TRAINING_DB_PORT']<1 || (int)$environment['TRAINING_DB_PORT']>65535) {
        throw new RuntimeException('Unsafe training-only database configuration');
    }
    // Reject accidental credential reuse when production variables are available.
    foreach (['USER','PASSWORD'] as $part) {
        if (isset($environment['DB_'.$part]) && $environment['DB_'.$part]===$environment['TRAINING_DB_'.$part]) {
            throw new RuntimeException('Training credentials must be independent');
        }
    }
    return array_intersect_key($environment,array_flip($required));
}

function training_db_connect(array $configuration): PDO {
    $ca=$configuration['TRAINING_DB_SSL_CA'];
    if (!is_file($ca) || !is_readable($ca) || ($pem=@file_get_contents($ca))===false || @openssl_x509_read($pem)===false) {
        throw new RuntimeException('Training CA missing, unreadable or invalid');
    }
    return new PDO('mysql:host='.$configuration['TRAINING_DB_HOST'].';port='.$configuration['TRAINING_DB_PORT'].';dbname=pc_forge_training;charset=utf8mb4',
        $configuration['TRAINING_DB_USER'],$configuration['TRAINING_DB_PASSWORD'],[
            PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES=>false,
            PDO::ATTR_TIMEOUT=>10,
            PDO::MYSQL_ATTR_MULTI_STATEMENTS=>false,
            PDO::MYSQL_ATTR_SSL_CA=>$ca,
            PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT=>true,
        ]);
}
