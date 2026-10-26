<?php
// Single-instance, bounded disk-backed budgets. No schema or credential changes.
function login_budget(string $email): int {
    $directory = getenv('PCFORGE_RATE_DIR') ?: sys_get_temp_dir().'/pc-forge-login';
    if (!is_dir($directory) && !@mkdir($directory, 0700, true) && !is_dir($directory)) {
        throw new RuntimeException('Login budget storage unavailable');
    }
    $handle = @fopen($directory.'/budgets.json', 'c+');
    if (!$handle) { throw new RuntimeException('Login budget storage unavailable'); }
    try {
        if (!flock($handle, LOCK_EX)) { throw new RuntimeException('Login budget lock unavailable'); }
        $raw = stream_get_contents($handle);
        $states = $raw === '' ? [] : json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
        if (!is_array($states)) { throw new RuntimeException('Invalid login budget storage'); }
        $now = time();
        foreach ($states as $key => $state) {
            if ($now-(int)$state['start']>=300) { unset($states[$key]); }
        }
        // Never pool unrelated users behind Render/NAT into one IP bucket.
        $keys = [hash('sha256','account:'.$email)=>15];
        $retry=0;
        foreach ($keys as $key=>$limit) {
            if (isset($states[$key]) && (int)$states[$key]['count'] >= $limit) {
                $retry=max($retry,300-($now-(int)$states[$key]['start']));
            }
        }
        // Refuse new budgets when capacity is reached; storage stays bounded.
        if (count($states)>=10000 && !isset($states[array_key_first($keys)])) { $retry=max($retry,300); }
        if (!$retry) {
            foreach ($keys as $key=>$limit) {
                $states[$key] ??= ['start'=>$now,'count'=>0];
                $states[$key]['count']++;
            }
        }
        $json=json_encode($states,JSON_THROW_ON_ERROR);
        rewind($handle);
        if (!ftruncate($handle,0) || fwrite($handle,$json)!==strlen($json) || !fflush($handle)) {
            throw new RuntimeException('Login budget write unavailable');
        }
        return $retry;
    } finally { flock($handle,LOCK_UN); fclose($handle); }
}
