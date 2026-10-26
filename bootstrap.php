<?php
session_start();require_once __DIR__.'/config/db.php';
function current_user(){return $_SESSION['user']??null;}
function require_login(){if(!current_user())redirect('login.php');}
function cart_count(){return array_sum(array_map('intval',$_SESSION['cart']??[]));}
