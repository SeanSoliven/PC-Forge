<?php
require __DIR__.'/bootstrap.php';
require __DIR__.'/layout.php';
$error='';
if ($_SERVER['REQUEST_METHOD']==='POST') {
    try {
        check_csrf();
        $name=trim(input($_POST,'name'));
        $email=strtolower(trim(input($_POST,'email')));
        $pass=input($_POST,'password');
        if (strlen($name)<2 || strlen($name)>120 || strlen($email)>190 || !filter_var($email,FILTER_VALIDATE_EMAIL) || strlen($pass)<8 || strlen($pass)>72 || str_contains($pass,"\0")) {
            throw new InvalidArgumentException('Enter a name (2-120 characters), valid email, and password of 8-72 bytes.');
        }
        $s=db()->prepare("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'customer')");
        $s->execute([$name,$email,password_hash($pass,PASSWORD_DEFAULT)]);
        redirect('login.php?registered=1');
    } catch (PDOException $e) {
        if (($e->errorInfo[1] ?? null)==1062) {
            http_response_code(422);
            $error='An account with this email already exists. Sign in or use another email.';
        } else { $error=request_error($e,'registration failed'); }
    } catch (Throwable $e) { $error=request_error($e,'registration failed'); }
}

head_html('Register');?><h1>Create an account</h1><?php if($error):?><p class="alert"><?=e($error)?></p><?php endif;?><form method="post" class="panel stack"><input type="hidden" name="csrf" value="<?=csrf()?>"><label>Name<input name="name" required minlength="2"></label><label>Email<input name="email" type="email" required></label><label>Password<input name="password" type="password" required minlength="8"></label><button class="btn">Register</button></form><?php foot_html();