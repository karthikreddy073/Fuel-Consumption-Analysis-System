CREATE DATABASE IF NOT EXISTS fuel_analysis;
USE fuel_analysis;

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_code VARCHAR(30) NOT NULL UNIQUE,
    vehicle_type VARCHAR(50) NOT NULL,
    fuel_type VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fuel_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    fill_date DATE NOT NULL,
    odometer_km DECIMAL(12,2) NOT NULL,
    litres DECIMAL(10,2) NOT NULL,
    total_cost DECIMAL(12,2) NOT NULL,
    full_tank_flag BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fuel_vehicle FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    INDEX idx_vehicle_date (vehicle_id, fill_date, record_id)
);

CREATE TABLE IF NOT EXISTS invalid_records (
    invalid_id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NULL,
    attempted_date DATE NULL,
    attempted_odometer DECIMAL(12,2) NULL,
    attempted_litres DECIMAL(10,2) NULL,
    attempted_cost DECIMAL(12,2) NULL,
    reason VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invalid_vehicle FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(vehicle_id) ON DELETE SET NULL
);

-- Optional sample vehicles. Run this file once in MySQL Workbench.
INSERT IGNORE INTO vehicles (vehicle_code, vehicle_type, fuel_type)
VALUES ('CAR-001', 'Car', 'Petrol'),
       ('BIKE-001', 'Bike', 'Petrol'),
       ('VAN-001', 'Van', 'Diesel');
