CREATE ROLE pos WITH
	LOGIN
	SUPERUSER
	CREATEDB
	CREATEROLE
	INHERIT
	NOREPLICATION
	BYPASSRLS
	CONNECTION LIMIT -1
	PASSWORD 'pointofsale';
COMMENT ON ROLE pos IS 'Point of sale user';

grant connect on database posdb to pos;

CREATE TABLE users (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'cashier'
);

INSERT INTO users
(
    username,
    password,
    name,
    role
)
VALUES
(
    'admin',
    'admin123',
    'Administrator',
    'manager'
)
ON CONFLICT (username) DO NOTHING;

CREATE TABLE products (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku TEXT UNIQUE,
    description TEXT NOT NULL,
    department TEXT,
    price REAL NOT NULL,
    quantity_on_hand INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
)

CREATE TABLE department (
    department_id BIGSERIAL PRIMARY KEY,
    sale_id BIGINT,
    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    department VARCHAR(20),
    price NUMERIC(12,2),
    z_id BIGINT,
    voided INTEGER DEFAULT 0,
    void_date TIMESTAMP,
    voided_by VARCHAR(50),

    CONSTRAINT fk_department_sales
        FOREIGN KEY (sale_id)
        REFERENCES sales(sale_id)
);

CREATE TABLE sales (
    sale_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subtotal NUMERIC(12,2),
    tax NUMERIC(12,2),
    total NUMERIC(12,2),
    cash_received NUMERIC(12,2),
    change_given NUMERIC(12,2),
    cashier VARCHAR(50),
    payment_type VARCHAR(20),
    check_number VARCHAR(50),
    card_last4 VARCHAR(4),
    z_id BIGINT,
    voided INTEGER DEFAULT 0,
    void_date TIMESTAMP,
    voided_by VARCHAR(50)
);

CREATE TABLE sale_items (
    sale_item_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sale_id BIGINT NOT NULL,
    sku VARCHAR(50),
    description VARCHAR(255),
    quantity INTEGER,
    price NUMERIC(12,2),
    cashier VARCHAR(50),
    CONSTRAINT fk_sale_items_sale
        FOREIGN KEY (sale_id)
        REFERENCES sales(sale_id)
        ON DELETE CASCADE
);

CREATE TABLE z_reports (
    z_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_count INTEGER,
    sales_total NUMERIC(12,2),
    tax_total NUMERIC(12,2)
);


CREATE INDEX idx_products_sku
    ON products(sku);

CREATE INDEX idx_sales_sale_date
    ON sales(sale_date);

CREATE INDEX idx_sales_zid
    ON sales(z_id);

CREATE INDEX idx_department_zid
    ON department(z_id);

CREATE INDEX idx_sale_items_saleid
    ON sale_items(sale_id);

INSERT INTO products
(
    sku,
    description,
    department,
    price,
    quantity_on_hand
)
VALUES
('1001','Coffee','DEPT001',2.50,100),
('1002','Bagel','DEPT001',1.75,50),
('1003','Sandwich','DEPT001',5.99,25),
('2001','Notebook','DEPT002',4.99,100),
('2002','Pen','DEPT002',1.25,250),
('3001','B&W Print','DEPT003',0.10,10000),
('3002','Color Print','DEPT003',0.50,5000)
ON CONFLICT (sku) DO NOTHING;


