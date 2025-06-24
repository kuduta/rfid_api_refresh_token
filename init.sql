CREATE DATABASE IF NOT EXISTS rfid_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE rfid_db;

CREATE TABLE IF NOT EXISTS rfid_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    epc VARCHAR(64),
    rssi INT,
    ipaddress VARCHAR(45),
    macaddress VARCHAR(32),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);