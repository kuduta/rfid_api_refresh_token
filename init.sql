CREATE DATABASE IF NOT EXISTS rfid_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE rfid_db;

CREATE TABLE IF NOT EXISTS rfid_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    epc VARCHAR(64) NOT NULL,
    rssi INT,
    ipaddress VARCHAR(45),
    client VARCHAR(64),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE client_status (
    client_name VARCHAR(50) PRIMARY KEY,
    ipaddress VARCHAR(50),
    last_seen DATETIME
);