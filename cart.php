<?php
require __DIR__.'/bootstrap.php';
require __DIR__.'/config/cart_limits.php';
require __DIR__.'/layout.php';

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        check_csrf();
        $id = (int)($_POST['product_id'] ?? 0);
        $action = $_POST['action'] ?? '';
        $cart = $_SESSION['cart'] ?? [];
        if (!is_array($cart)) { throw new InvalidArgumentException('Invalid cart contents.'); }

        if ($action === 'clear') {
            $cart = [];
        } elseif ($action === 'remove') {
            unset($cart[$id]);
        } elseif ($action === 'add' || $action === 'update') {
            $statement = db()->prepare('SELECT stock FROM products WHERE id=? AND is_active=1');
            $statement->execute([$id]);
            $stock = $statement->fetchColumn();
            if ($stock === false) { throw new InvalidArgumentException('Product unavailable'); }

            $current = (int)($cart[$id] ?? 0);
            $quantity = $action === 'update'
                ? filter_var($_POST['quantity'] ?? null, FILTER_VALIDATE_INT)
                : $current + 1;
            if ($quantity === false || $quantity < 1 || $quantity > CART_MAX_QUANTITY_PER_PRODUCT) {
                throw new InvalidArgumentException('Each product is limited to '.CART_MAX_QUANTITY_PER_PRODUCT.' items.');
            }
            if ($quantity > (int)$stock) { throw new InvalidArgumentException('Not enough stock'); }
            if (!array_key_exists($id, $cart) && count($cart) >= CART_MAX_LINES) {
                throw new InvalidArgumentException('Your cart can contain at most '.CART_MAX_LINES.' different products.');
            }
            $newTotal = cart_total_quantity($cart) - $current + $quantity;
            if ($newTotal > CART_MAX_TOTAL_QUANTITY) {
                throw new InvalidArgumentException('Your cart is limited to '.CART_MAX_TOTAL_QUANTITY.' items total.');
            }
            $cart[$id] = $quantity;
        } else {
            throw new InvalidArgumentException('Invalid cart action');
        }

        $_SESSION['cart'] = $cart;
        unset($_SESSION['checkout_token']);
        redirect('cart.php');
    } catch (Throwable $exception) {
        $error = request_error($exception, 'cart.php failed');
    }
}

$cart = $_SESSION['cart'] ?? [];
if (!is_array($cart)) { $cart = []; }
$items = [];
$total = 0;
if ($cart) {
    $ids = array_map('intval', array_keys($cart));
    $placeholders = implode(',', array_fill(0, count($ids), '?'));
    $statement = db()->prepare("SELECT * FROM products WHERE is_active=1 AND id IN ($placeholders)");
    $statement->execute($ids);
    $items = $statement->fetchAll();
    $available = array_map('intval', array_column($items, 'id'));
    foreach (array_keys($cart) as $id) {
        if (!in_array((int)$id, $available, true)) {
            unset($_SESSION['cart'][$id], $cart[$id]);
            unset($_SESSION['checkout_token']);
        }
    }
    foreach ($items as $item) { $total += (float)$item['price'] * $cart[$item['id']]; }
}

head_html('Cart');
?>
<h1>Your cart</h1>
<?php if ($error): ?><p class="alert"><?=e($error)?></p><?php endif; ?>
<?php if (!$items): ?>
<p>Cart is empty. <a class="accent" href="index.php">Browse parts →</a></p>
<?php else: ?>
<div class="panel"><table class="table"><tr><th>Item</th><th>Qty</th><th>Subtotal</th><th></th></tr>
<?php foreach ($items as $item): ?>
<tr><td><?=e($item['name'])?></td><td><form method="post" class="flex">
<input type="hidden" name="csrf" value="<?=csrf()?>"><input type="hidden" name="product_id" value="<?=(int)$item['id']?>">
<input type="number" name="quantity" min="1" max="<?=CART_MAX_QUANTITY_PER_PRODUCT?>" value="<?=(int)$cart[$item['id']]?>" style="width:85px">
<button class="btn alt" name="action" value="update">Update</button></form></td>
<td>₱<?=number_format($item['price'] * $cart[$item['id']], 2)?></td>
<td><form method="post"><input type="hidden" name="csrf" value="<?=csrf()?>"><input type="hidden" name="product_id" value="<?=(int)$item['id']?>"><button class="btn alt" name="action" value="remove">Remove</button></form></td></tr>
<?php endforeach; ?></table><h2>Total: ₱<?=number_format($total, 2)?></h2><a class="btn" href="checkout.php">Checkout →</a></div>
<?php endif; ?>
<?php foot_html(); ?>
