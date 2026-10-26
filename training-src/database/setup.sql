-- Manually run as an authorized owner on your existing Aiven service.
-- Creates ONLY the separate pc_forge_training database; no production tables.
-- No production connection, credentials, or schema imports. Not run by startup.
CREATE DATABASE pc_forge_training CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- All table names are qualified, even if a SQL client continues after an error.
CREATE TABLE pc_forge_training.users (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(120) NOT NULL, email VARCHAR(190) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL,
 demo_password VARCHAR(100) NOT NULL COMMENT 'Synthetic teaching data only',
 role ENUM('customer','admin') NOT NULL
) ENGINE=InnoDB;
CREATE TABLE pc_forge_training.products (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(200) NOT NULL, price DECIMAL(12,2) NOT NULL, stock INT UNSIGNED NOT NULL
) ENGINE=InnoDB;
INSERT INTO pc_forge_training.users(name,email,password_hash,demo_password,role) VALUES
('Synthetic Customer','customer@training.test','$2y$10$swV2yCEl5AjzWKl/0qC/AOZ1/VaTsK2sLN949XWtXGWi.I5SB34KG','lab-customer-123','customer'),
('Synthetic Administrator','admin@training.test','$2y$10$d8QqWmP5XQseorIzJO1XV.Y.OIYQprq1.Js9ODZ9ImLJCkMufiZXu','lab-admin-123','admin');
INSERT INTO pc_forge_training.products(name,price,stock) VALUES ('Synthetic CPU',11995,12),('Synthetic GPU',19995,7);
-- Next: create the zero-privilege Aiven user using aiven-user-request.json,
-- then apply grants.sql manually. See AIVEN_SETUP.md. Never reuse DB_USER.
