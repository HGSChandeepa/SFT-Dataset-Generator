-- Example SQL Schema for E-commerce Database

CREATE TABLE customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(50),
    country VARCHAR(50),
    registration_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    supplier VARCHAR(100),
    created_date DATE NOT NULL
);

CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Sample Data

INSERT INTO customers (name, email, phone, address, city, country, registration_date, status) VALUES
('Alice Johnson', 'alice.johnson@email.com', '+1-555-0101', '123 Main St', 'New York', 'USA', '2023-01-15', 'active'),
('Bob Smith', 'bob.smith@email.com', '+1-555-0102', '456 Oak Ave', 'Los Angeles', 'USA', '2023-02-20', 'active'),
('Carol Williams', 'carol.w@email.com', '+44-20-1234-5678', '789 High Street', 'London', 'UK', '2023-03-10', 'active'),
('David Brown', 'david.brown@email.com', '+1-555-0104', '321 Pine Rd', 'Chicago', 'USA', '2023-04-05', 'inactive'),
('Emma Davis', 'emma.davis@email.com', '+61-2-9876-5432', '654 Beach Blvd', 'Sydney', 'Australia', '2023-05-12', 'active'),
('Frank Miller', 'frank.m@email.com', '+1-555-0106', '987 Elm St', 'Boston', 'USA', '2023-06-18', 'active'),
('Grace Lee', 'grace.lee@email.com', '+82-2-1234-5678', '147 Seoul Ave', 'Seoul', 'South Korea', '2023-07-22', 'active'),
('Henry Wilson', 'henry.wilson@email.com', '+1-555-0108', '258 Maple Dr', 'Seattle', 'USA', '2023-08-30', 'active');

INSERT INTO products (name, description, category, price, stock_quantity, supplier, created_date) VALUES
('Laptop Pro 15', 'High-performance laptop with 16GB RAM', 'Electronics', 1299.99, 45, 'TechCorp', '2023-01-01'),
('Wireless Mouse', 'Ergonomic wireless mouse with USB receiver', 'Electronics', 29.99, 200, 'AccessoriesInc', '2023-01-01'),
('USB-C Cable', 'Durable 2-meter USB-C charging cable', 'Electronics', 15.99, 350, 'AccessoriesInc', '2023-01-01'),
('Office Chair', 'Ergonomic office chair with lumbar support', 'Furniture', 299.99, 25, 'FurnitureWorld', '2023-01-15'),
('Standing Desk', 'Adjustable height standing desk', 'Furniture', 599.99, 15, 'FurnitureWorld', '2023-01-15'),
('Mechanical Keyboard', 'RGB mechanical keyboard with blue switches', 'Electronics', 149.99, 80, 'TechCorp', '2023-02-01'),
('Monitor 27"', '4K UHD 27-inch monitor', 'Electronics', 449.99, 30, 'TechCorp', '2023-02-01'),
('Desk Lamp', 'LED desk lamp with adjustable brightness', 'Furniture', 39.99, 120, 'FurnitureWorld', '2023-02-15'),
('Webcam HD', '1080p HD webcam with built-in microphone', 'Electronics', 79.99, 60, 'TechCorp', '2023-03-01'),
('Noise-Canceling Headphones', 'Premium wireless headphones with ANC', 'Electronics', 249.99, 40, 'AudioTech', '2023-03-01');

INSERT INTO orders (customer_id, order_date, total_amount, status, shipping_address) VALUES
(1, '2023-09-01', 1329.98, 'delivered', '123 Main St, New York, USA'),
(1, '2023-09-15', 449.99, 'delivered', '123 Main St, New York, USA'),
(2, '2023-09-03', 299.99, 'delivered', '456 Oak Ave, Los Angeles, USA'),
(3, '2023-09-05', 179.98, 'shipped', '789 High Street, London, UK'),
(4, '2023-09-07', 599.99, 'cancelled', '321 Pine Rd, Chicago, USA'),
(5, '2023-09-10', 1799.96, 'delivered', '654 Beach Blvd, Sydney, Australia'),
(6, '2023-09-12', 45.98, 'delivered', '987 Elm St, Boston, USA'),
(7, '2023-09-14', 329.98, 'processing', '147 Seoul Ave, Seoul, South Korea'),
(8, '2023-09-16', 899.97, 'shipped', '258 Maple Dr, Seattle, USA'),
(1, '2023-09-20', 249.99, 'processing', '123 Main St, New York, USA');

INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 1, 1299.99, 1299.99),
(1, 2, 1, 29.99, 29.99),
(2, 7, 1, 449.99, 449.99),
(3, 4, 1, 299.99, 299.99),
(4, 6, 1, 149.99, 149.99),
(4, 2, 1, 29.99, 29.99),
(5, 5, 1, 599.99, 599.99),
(6, 1, 1, 1299.99, 1299.99),
(6, 7, 1, 449.99, 449.99),
(6, 9, 1, 79.99, 79.99),
(7, 3, 2, 15.99, 31.98),
(7, 8, 1, 39.99, 39.99),
(8, 10, 1, 249.99, 249.99),
(8, 9, 1, 79.99, 79.99),
(9, 1, 1, 1299.99, 1299.99),
(9, 6, 1, 149.99, 149.99),
(9, 2, 1, 29.99, 29.99),
(10, 10, 1, 249.99, 249.99);