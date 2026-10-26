-- Disposable CI MySQL ONLY. No real data or credentials. Not an Aiven setup file.
CREATE DATABASE mens_daydb;
CREATE TABLE mens_daydb.users (id INT PRIMARY KEY, name VARCHAR(80));
INSERT INTO mens_daydb.users VALUES (1,'Synthetic unrelated fixture');
CREATE USER 'pc_forge_training_reader'@'%' IDENTIFIED BY 'synthetic-training-readonly-secret' REQUIRE SSL;
