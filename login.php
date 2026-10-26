<?php
require __DIR__.'/bootstrap.php';
require __DIR__.'/layout.php';
$error='';
if ($_SERVER['REQUEST_METHOD']==='POST') {
    try {
        check_csrf();
        $email=strtolower(trim(input($_POST,'email')));
        $password=input($_POST,'password');
        $s=db()->prepare('SELECT id,name,email,password_hash,role FROM users WHERE email=?');
        $s->execute([$email]);
        $u=$s->fetch();
        if (!$u || !password_verify($password,$u['password_hash']) || !in_array($u['role'],['customer','admin'],true)) {
            throw new InvalidArgumentException('Invalid email or password.');
        }
        if (!session_regenerate_id(true)) { throw new RuntimeException('Session regeneration failed'); }
        unset($u['password_hash'], $_SESSION['csrf']);
        $_SESSION['user']=$u;
        redirect($u['role']==='admin' ? 'admin/index.php' : 'index.php');
    } catch (Throwable $e) { $error=request_error($e,'login failed'); }
}

head_html('Login');?><h1>Sign in</h1><?php if(isset($_GET['registered'])):?><p class="alert success">Account created. Sign in below.</p><?php endif;?><?php if($error):?><p class="alert"><?=e($error)?></p><?php endif;?><form method="post" class="panel stack"><input type="hidden" name="csrf" value="<?=csrf()?>"><label>Email<input type="email" name="email" required></label><label>Password<input type="password" name="password" required></label><button class="btn">Login</button></form><?php foot_html();
