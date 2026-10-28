<?php
// Explicit bounds prevent session cart growth if inventory or catalog size changes.
const CART_MAX_LINES = 5;
const CART_MAX_QUANTITY_PER_PRODUCT = 5;
const CART_MAX_TOTAL_QUANTITY = 10;

function cart_total_quantity(array $cart): int {
    $total = 0;
    foreach ($cart as $quantity) {
        if (!is_int($quantity) || $quantity < 0) {
            throw new InvalidArgumentException('Invalid cart contents.');
        }
        $total += $quantity;
    }
    return $total;
}
