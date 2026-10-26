<?php
function db(): PDO {
 static $pdo=null;
 if($pdo) return $pdo;
 $host=getenv('DB_HOST'); $port=getenv('DB_PORT') ?: '3306'; $name=getenv('DB_NAME') ?: 'pc_forge';
 $user=getenv('DB_USER'); $pass=getenv('DB_PASSWORD');
 if(!$host || !$user || $pass===false) throw new RuntimeException('Database configuration missing');
 $opts=[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,PDO::ATTR_EMULATE_PREPARES=>false];
 $ca=getenv('DB_SSL_CA');
 if($ca){$opts[PDO::MYSQL_ATTR_SSL_CA]=$ca;$opts[PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT]=true;}
 $pdo=new PDO("mysql:host=$host;port=$port;dbname=$name;charset=utf8mb4",$user,$pass,$opts);
 return $pdo;
}
function e($v){return htmlspecialchars((string)$v,ENT_QUOTES,'UTF-8');}
function csrf(){if(empty($_SESSION['csrf']))$_SESSION['csrf']=bin2hex(random_bytes(32));return $_SESSION['csrf'];}
function check_csrf(){if(!hash_equals($_SESSION['csrf']??'',$_POST['csrf']??''))throw new RuntimeException('Invalid request token');}
function redirect($to){header('Location: '.$to);exit;}
