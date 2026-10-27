<?php
// Failed-login counts and cooldowns persist across requests on this app instance.
function login_attempt(string $email, string $action): int {
    if (!in_array($action, ['check', 'failed', 'success'], true)) {
        throw new InvalidArgumentException('Invalid login attempt action.');
    }

    $directory = getenv('PCFORGE_RATE_DIR') ?: sys_get_temp_dir().'/pc-forge-login';
    if (!is_dir($directory) && !@mkdir($directory, 0700, true) && !is_dir($directory)) {
        throw new RuntimeException('Login attempt storage unavailable');
    }
    $handle = @fopen($directory.'/budgets.json', 'c+');
    if (!$handle) { throw new RuntimeException('Login attempt storage unavailable'); }

    try {
        if (!flock($handle, LOCK_EX)) { throw new RuntimeException('Login attempt lock unavailable'); }
        $raw = stream_get_contents($handle);
        $states = $raw === '' ? [] : json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
        if (!is_array($states)) { throw new RuntimeException('Invalid login attempt storage'); }

        $key = hash('sha256', 'account:'.$email);
        $now = time();
        foreach ($states as $stateKey => $state) {
            if (!is_array($state) || !isset($state['failures'], $state['locked_until'])) {
                unset($states[$stateKey]);
            } elseif ((int)$state['locked_until'] > 0 && (int)$state['locked_until'] <= $now) {
                unset($states[$stateKey]);
            }
        }

        $retry = 0;
        if ($action === 'success') {
            unset($states[$key]);
        } elseif (isset($states[$key]) && (int)$states[$key]['locked_until'] > $now) {
            $retry = (int)$states[$key]['locked_until'] - $now;
        } elseif (count($states) >= 10000 && !isset($states[$key])) {
            // Keep storage bounded and fail closed if it cannot track another account.
            $retry = 120;
        } elseif ($action === 'failed') {
            $states[$key] = [
                'failures' => (int)($states[$key]['failures'] ?? 0) + 1,
                'locked_until' => 0
            ];
            if ($states[$key]['failures'] >= 5) {
                // Five consecutive failures lock the account for two minutes.
                $states[$key]['locked_until'] = $now + 120;
                $retry = 120;
            }
        }

        $json = json_encode($states, JSON_THROW_ON_ERROR);
        rewind($handle);
        if (!ftruncate($handle, 0) || fwrite($handle, $json) !== strlen($json) || !fflush($handle)) {
            throw new RuntimeException('Login attempt storage write unavailable');
        }
        return $retry;
    } finally {
        flock($handle, LOCK_UN);
        fclose($handle);
    }
}
