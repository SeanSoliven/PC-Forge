-- OPTIONAL alternative to Aiven API user creation, only if Aiven permits it.
-- DO NOT RUN if the dedicated user already exists. No IF NOT EXISTS fallback.
-- MySQL 8 generates a fresh password; save its result privately, never in Git/logs.
-- No password literal, global privilege, or role is granted here.
CREATE USER 'pc_forge_training_reader'@'%' IDENTIFIED BY RANDOM PASSWORD REQUIRE SSL;
