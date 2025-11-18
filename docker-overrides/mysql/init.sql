-- Init script to create application user and grant privileges
CREATE DATABASE IF NOT EXISTS teadb;
CREATE USER IF NOT EXISTS 'teauser'@'%' IDENTIFIED BY 'teapass';
GRANT ALL PRIVILEGES ON teadb.* TO 'teauser'@'%';
FLUSH PRIVILEGES;
-- Ensure root has the expected password (no-op if already set)
ALTER USER 'root'@'localhost' IDENTIFIED BY 'rootpass' DEFAULT ROLE ALL;
