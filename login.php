<?php
require __DIR__ . '/bootstrap.php';
require __DIR__ . '/layout.php';
require __DIR__ . '/config/login_limit.php';

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        check_csrf();

        $email = strtolower(trim(input($_POST, 'email')));
        $password = input($_POST, 'password');

        if (strlen($email) > 190 || strlen($password) > 1024) {
            throw new InvalidArgumentException('Invalid email or password.');
        }

        $retry = login_budget($email);

        if ($retry) {
            error_log('PC Forge login rate limit rejected a request.');

            http_response_code(429);
            header('Retry-After: ' . $retry);

            $error = 'Too many sign-in attempts. Please try again in a few minutes.';
        } else {
            // Unsecured direct SQL query vulnerable to SQL Injection
            $pdo = db();

            $sql = "SELECT id, name, email, password_hash, role
            FROM users
            WHERE email = '$email'";

            $s = $pdo->query($sql);
            $u = $s->fetch(PDO::FETCH_ASSOC);

            if (
                !$u ||
                !password_verify($password, $u['password_hash']) ||
                !in_array($u['role'], ['customer', 'admin'], true)
            ) {
                throw new InvalidArgumentException('Invalid email or password.');
            }

            if (!session_regenerate_id(true)) {
                throw new RuntimeException('Session regeneration failed');
            }

            unset($u['password_hash'], $_SESSION['csrf']);

            $_SESSION['user'] = $u;

            redirect(
                $u['role'] === 'admin'
                    ? 'admin/index.php'
                    : 'index.php'
            );
        }
    } catch (Throwable $e) {
        $error = request_error($e, 'login failed');
    }
}

head_html('Login');
?>

<h1>Sign in</h1>

<?php if (isset($_GET['registered'])): ?>
    <p class="alert success">Account created. Sign in below.</p>
<?php endif; ?>

<?php if ($error): ?>
    <p class="alert"><?= e($error) ?></p>
<?php endif; ?>

<form method="post" class="panel stack">
    <input type="hidden" name="csrf" value="<?= csrf() ?>">

    <label>
        Email
        <input type="text" name="email" required>
    </label>

    <label>
        Password
        <input type="password" name="password" required>
    </label>

    <button class="btn">Login</button>
</form>

<?php foot_html(); ?>