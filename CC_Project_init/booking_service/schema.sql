CREATE DATABASE IF NOT EXISTS booking_services;
USE train_booking;

CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pnr VARCHAR(20) UNIQUE,
    transaction_id VARCHAR(30),
    train_number VARCHAR(10),
    train_name VARCHAR(100),
    from_station VARCHAR(10),
    to_station VARCHAR(10),
    journey_date DATE,
    booking_date DATE,
    quota VARCHAR(10),
    boarding_point VARCHAR(10),
    class VARCHAR(5),
    reservation_upto VARCHAR(10),
    amount DECIMAL(10, 2)
);

CREATE TABLE passengers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT,
    name VARCHAR(100),
    age INT,
    gender VARCHAR(10),
    booking_status VARCHAR(20),
    current_status VARCHAR(10),
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);
