-- Manually run as the TRAINING owner on the separate synthetic database only.
-- The read-only runtime account must not be permitted to execute this reset.
-- All table names are qualified, even if a SQL client continues after an error.
START TRANSACTION;
UPDATE pc_forge_training.users SET name='Synthetic Customer',role='customer',
 password_hash='$2y$10$swV2yCEl5AjzWKl/0qC/AOZ1/VaTsK2sLN949XWtXGWi.I5SB34KG',
 demo_password='lab-customer-123' WHERE email='customer@training.test';
UPDATE pc_forge_training.users SET name='Synthetic Administrator',role='admin',
 password_hash='$2y$10$d8QqWmP5XQseorIzJO1XV.Y.OIYQprq1.Js9ODZ9ImLJCkMufiZXu',
 demo_password='lab-admin-123' WHERE email='admin@training.test';
UPDATE pc_forge_training.products SET stock=12 WHERE name='Synthetic CPU';
UPDATE pc_forge_training.products SET stock=7 WHERE name='Synthetic GPU';
COMMIT;
