<?php

// Serialize status changes and stock restoration with checkout's inventory locks.
function change_order_status(PDO $pdo, int $id, string $status): void {
    $allowed = [
        'pending' => ['processing', 'cancelled'],
        'processing' => ['shipped', 'cancelled'],
        'shipped' => ['delivered'],
        'delivered' => [],
        'cancelled' => [],
    ];
    $pdo->beginTransaction();
    try {
        $statement = $pdo->prepare('SELECT status FROM orders WHERE id=? FOR UPDATE');
        $statement->execute([$id]);
        $current = $statement->fetchColumn();
        if ($current === false) { throw new InvalidArgumentException('Order not found.'); }
        if ($current !== $status) {
            if (!in_array($status, $allowed[$current] ?? [], true)) {
                throw new InvalidArgumentException('This order status transition is not allowed.');
            }
            if ($status === 'cancelled') {
                $statement = $pdo->prepare('SELECT product_id,quantity FROM order_items WHERE order_id=? ORDER BY product_id');
                $statement->execute([$id]);
                foreach ($statement->fetchAll() as $item) {
                    $update = $pdo->prepare('UPDATE products SET stock=stock+? WHERE id=?');
                    $update->execute([$item['quantity'], $item['product_id']]);
                }
            }
            $statement = $pdo->prepare('UPDATE orders SET status=? WHERE id=?');
            $statement->execute([$status, $id]);
        }
        $pdo->commit();
    } catch (Throwable $error) {
        if ($pdo->inTransaction()) { $pdo->rollBack(); }
        throw $error;
    }
}
