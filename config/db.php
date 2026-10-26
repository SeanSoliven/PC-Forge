
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
        throw new RuntimeException(
            'Database configuration missing'
        );
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

        error_log(
            'SSL CA exists: ' .
            (is_file($ca) ? 'YES' : 'NO')
        );

        error_log(
            'SSL CA readable: ' .
            (is_readable($ca) ? 'YES' : 'NO')
        );

        // Safely read the certificate
        $contents = is_readable($ca)
            ? file_get_contents($ca)
            : false;

        // Validate PEM certificate format
        $cert = $contents !== false
            ? @openssl_x509_read($contents)
            : false;

        error_log(
            'SSL CA valid PEM: ' .
            ($cert !== false ? 'YES' : 'NO')
        );

        if ($cert === false) {
            throw new RuntimeException(
                'Aiven SSL certificate is invalid or unreadable'
            );
        }

        // Configure PDO MySQL SSL
        $opts[PDO::MYSQL_ATTR_SSL_CA] = $ca;
        $opts[PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT] = true;

    } else {
        throw new RuntimeException(
            'DB_SSL_CA is not configured'
        );
    }

    // Connect to Aiven MySQL
    try {
        $pdo = new PDO(
            "mysql:host=$host;port=$port;dbname=$name;charset=utf8mb4",
            $user,
            $pass,
            $opts
        );

        error_log('Aiven MySQL connection successful');

        return $pdo;

    } catch (PDOException $e) {

        // Log technical details privately
        error_log(
            'Aiven MySQL connection failed: ' .
            $e->getMessage()
        );

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
