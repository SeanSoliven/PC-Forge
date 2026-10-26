
<?php

function db(): PDO {
    static $pdo = null;

    if ($pdo !== null) {
        return $pdo;
    }

    // Aiven MySQL environment variables
    $host = getenv('DB_HOST');
    $port = getenv('DB_PORT') ?: '3306';
    $name = getenv('DB_NAME') ?: 'pc_forge';
    $user = getenv('DB_USER');
    $pass = getenv('DB_PASSWORD');

    // Check required database configuration
    if (!$host || !$user || $pass === false) {
        error_log('PC Forge database configuration missing required environment variables.');
        throw new RuntimeException('Database connection unavailable');
    }

    // PDO configuration
    $opts = [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false
    ];

    // Aiven SSL certificate configuration
    $ca = getenv('DB_SSL_CA');

    if ($ca) {

        // Never fall back to an unencrypted connection when validation fails.
        $exists = is_file($ca);
        $readable = $exists && is_readable($ca);
        $contents = $readable
            ? @file_get_contents($ca)
            : false;

        // Validate PEM certificate format
        $cert = $contents !== false
            ? @openssl_x509_read($contents)
            : false;

        if ($cert === false) {
            error_log(sprintf(
                'PC Forge SSL CA validation failed: exists=%s readable=%s parseable_PEM=NO',
                $exists ? 'YES' : 'NO',
                $readable ? 'YES' : 'NO'
            ));
            throw new RuntimeException('Database connection unavailable');
        }

        // Configure PDO MySQL SSL
        $opts[PDO::MYSQL_ATTR_SSL_CA] = $ca;
        $opts[PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT] = true;

    } else {
        error_log('PC Forge database configuration missing DB_SSL_CA.');
        throw new RuntimeException('Database connection unavailable');
    }

    // Connect to Aiven MySQL
    try {
        $pdo = new PDO(
            "mysql:host=$host;port=$port;dbname=$name;charset=utf8mb4",
            $user,
            $pass,
            $opts
        );

        return $pdo;

    } catch (PDOException $e) {

        // Driver messages may contain usernames or connection details. Log codes only.
        $sqlState = $e->errorInfo[0] ?? 'unknown';
        $driverCode = $e->errorInfo[1] ?? 'unknown';
        error_log(sprintf(
            'PC Forge MySQL connection failed: SQLSTATE=%s driver_code=%s',
            $sqlState,
            $driverCode
        ));

        // Avoid exposing credentials or internal paths
        throw new RuntimeException(
            'Database connection unavailable'
        );
    }
}

// Escape HTML output
function e($v): string {
    return htmlspecialchars(
        (string) $v,
        ENT_QUOTES,
        'UTF-8'
    );
}

// Generate CSRF token
function csrf(): string {
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(
            random_bytes(32)
        );
    }

    return $_SESSION['csrf'];
}

// Validate CSRF token
function check_csrf(): void {
    if (
        !hash_equals(
            $_SESSION['csrf'] ?? '',
            $_POST['csrf'] ?? ''
        )
    ) {
        throw new RuntimeException(
            'Invalid request token'
        );
    }
}

// Redirect helper
function redirect($to): void {
    header('Location: ' . $to);
    exit;
}
