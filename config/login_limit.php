<?php
function login_attempt(string $email, string $action): array {
    if (!in_array($action, ['check', 'failed', 'success'], true)) {
        throw new InvalidArgumentException('Invalid login attempt action.');
    }

    $pdo = db();
    $key = hash('sha256', 'account:' . $email);
    $now = time();

    if ($action === 'check') {
        $statement = $pdo->prepare(
            'SELECT failed_attempts, locked_until FROM login_attempts WHERE account_key = ?'
        );
        $statement->execute([$key]);
        $state = $statement->fetch(PDO::FETCH_ASSOC);

        if (!$state) {
            return ['failures' => 0, 'locked_until' => 0];
        }

        $failures = (int) $state['failed_attempts'];
        $lockedUntil = (int) $state['locked_until'];
        if ($lockedUntil > 0 && $lockedUntil <= $now) {
            $reset = $pdo->prepare(
                'UPDATE login_attempts SET failed_attempts = 0, locked_until = 0
                 WHERE account_key = ? AND locked_until = ?'
            );
            $reset->execute([$key, $lockedUntil]);

            return ['failures' => 0, 'locked_until' => 0];
        }

        return ['failures' => $failures, 'locked_until' => $lockedUntil];
    }

    $pdo->beginTransaction();
    try {
        $insert = $pdo->prepare(
            'INSERT IGNORE INTO login_attempts (account_key) VALUES (?)'
        );
        $insert->execute([$key]);

        $select = $pdo->prepare(
            'SELECT failed_attempts, locked_until FROM login_attempts
             WHERE account_key = ? FOR UPDATE'
        );
        $select->execute([$key]);
        $state = $select->fetch(PDO::FETCH_ASSOC);
        if (!$state) {
            throw new RuntimeException('Login attempt storage unavailable');
        }

        $failures = (int) $state['failed_attempts'];
        $lockedUntil = (int) $state['locked_until'];

        if ($action === 'success' && $lockedUntil > $now) {
            // A concurrent fifth failure must not be bypassed by an in-flight login.
        } elseif ($action === 'success') {
            $failures = 0;
            $lockedUntil = 0;
        } elseif ($lockedUntil > $now) {
            // A concurrent request may have started the cooldown after its initial check.
        } else {
            if ($lockedUntil > 0 || $failures >= 5) {
                $failures = 0;
            }
            $failures++;
            $lockedUntil = $failures >= 5 ? $now + 120 : 0;
        }

        $update = $pdo->prepare(
            'UPDATE login_attempts SET failed_attempts = ?, locked_until = ? WHERE account_key = ?'
        );
        $update->execute([$failures, $lockedUntil, $key]);
        $pdo->commit();

        return ['failures' => $failures, 'locked_until' => $lockedUntil];
    } catch (Throwable $error) {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
        throw $error;
    }
}
