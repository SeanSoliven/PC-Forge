<?php
require __DIR__ . '/bootstrap.php';
require __DIR__ . '/layout.php';
require __DIR__ . '/config/login_limit.php';

$error = '';
$loginStatus = ['failures' => 0, 'locked_until' => 0];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        check_csrf();

        $email = strtolower(trim(input($_POST, 'email')));
        $password = input($_POST, 'password');

        if (strlen($email) > 190 || strlen($password) > 1024) {
            throw new InvalidArgumentException('Invalid email or password.');
        }

        $loginStatus = login_attempt($email, 'check');

        if ($loginStatus['locked_until'] > time()) {
            error_log('PC Forge login rate limit rejected a request.');
            $_SESSION['login_attempt_email'] = $email;
            header('Retry-After: ' . ($loginStatus['locked_until'] - time()));
            redirect('login.php');
        } else {
            $s = db()->prepare(
                'SELECT id, name, email, password_hash, role FROM users WHERE email = ?'
            );
            $s->execute([$email]);
            $u = $s->fetch(PDO::FETCH_ASSOC);

            if (
                !$u ||
                !password_verify($password, $u['password_hash']) ||
                !in_array($u['role'], ['customer', 'admin'], true)
            ) {
                $loginStatus = login_attempt($email, 'failed');
                $_SESSION['login_attempt_email'] = $email;
                if ($loginStatus['locked_until'] > time()) {
                    header('Retry-After: ' . ($loginStatus['locked_until'] - time()));
                }
                redirect('login.php');
            } elseif (!session_regenerate_id(true)) {
                throw new RuntimeException('Session regeneration failed');
            } else {
                $loginStatus = login_attempt($email, 'success');
                if ($loginStatus['locked_until'] > time()) {
                    $_SESSION['login_attempt_email'] = $email;
                    header('Retry-After: ' . ($loginStatus['locked_until'] - time()));
                    redirect('login.php');
                }

                unset($u['password_hash'], $_SESSION['csrf'], $_SESSION['login_attempt_email']);

                $_SESSION['user'] = $u;

                redirect(
                    $u['role'] === 'admin'
                    ? 'admin/index.php'
                    : 'index.php'
                );
            }
        }
    } catch (Throwable $e) {
        $error = request_error($e, 'login failed');
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'GET' && isset($_SESSION['login_attempt_email'])) {
    try {
        $loginStatus = login_attempt($_SESSION['login_attempt_email'], 'check');
        if ($loginStatus['locked_until'] > time()) {
            header('Retry-After: ' . ($loginStatus['locked_until'] - time()));
        } elseif ($loginStatus['failures'] > 0) {
            $attemptsRemaining = 5 - $loginStatus['failures'];
            $attemptWord = $attemptsRemaining === 1 ? 'attempt' : 'attempts';
            $error = 'Invalid email or password. '
                . $attemptsRemaining . ' ' . $attemptWord . ' remaining.';
        } else {
            unset($_SESSION['login_attempt_email']);
        }
    } catch (Throwable $e) {
        $error = request_error($e, 'login attempt status');
    }
}

$isLocked = $loginStatus['locked_until'] > time();
$lockoutMessage = '';
if ($isLocked) {
    $remainingSeconds = max(0, $loginStatus['locked_until'] - time());
    $lockoutMessage = 'Too many failed login attempts. Please try again in '
        . gmdate('i:s', $remainingSeconds) . '.';
}

head_html('Login');
?>

<h1>Sign in</h1>

<?php if (isset($_GET['registered'])): ?>
    <p class="alert success">Account created. Sign in below.</p>
<?php endif; ?>

<form method="post" class="panel stack">
    <input type="hidden" name="csrf" value="<?= csrf() ?>">

    <label>
        Email
        <input type="text" name="email" value="<?= e($_SESSION['login_attempt_email'] ?? '') ?>" required>
    </label>

    <label>
        Password
        <input type="password" name="password" required>
    </label>

    <button class="btn" id="login-button" <?= $isLocked ? 'disabled' : '' ?>>Login</button>
</form>

<?php if ($error || $isLocked): ?>
    <p
        class="alert"
        id="login-error"
        role="alert"
        <?php if ($isLocked): ?>
            data-lockout-until="<?= e($loginStatus['locked_until']) ?>"
        <?php endif; ?>
    ><?= e($isLocked ? $lockoutMessage : $error) ?></p>
<?php endif; ?>

<script src="assets/login.js" defer></script>

<?php foot_html(); ?>