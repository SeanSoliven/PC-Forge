-- Owner-only, MANUAL. Only for the NEW zero-privilege dedicated account.
-- Check its actual account host in Aiven before running; '%' is the expected host.
-- If this account has other grants/roles, STOP; do not run this on DB_USER/avnadmin.
-- Do not substitute global SELECT, schema wildcards, or WITH GRANT OPTION.
ALTER USER 'pc_forge_training_reader'@'%' REQUIRE SSL;
GRANT SELECT ON pc_forge_training.users TO 'pc_forge_training_reader'@'%';
GRANT SELECT ON pc_forge_training.products TO 'pc_forge_training_reader'@'%';
SHOW GRANTS FOR 'pc_forge_training_reader'@'%';
