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

CREATE TABLE IF NOT EXISTS public.department
(
    department_id bigserial NOT NULL,
    sale_id bigint,
    sale_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    department character varying(20) COLLATE pg_catalog."default",
    price numeric(12,2),
    z_id bigint,
    voided integer DEFAULT 0,
    void_date timestamp without time zone,
    voided_by character varying(50) COLLATE pg_catalog."default",
    register_id integer,
    quantity integer,
    CONSTRAINT department_pkey PRIMARY KEY (department_id)
)


CREATE TABLE IF NOT EXISTS public.sales
(
    sale_id integer NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
    sale_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    subtotal numeric(12,2),
    tax numeric(12,2),
    total numeric(12,2),
    cash_received numeric(12,2),
    change_given numeric(12,2),
    cashier character varying(50) COLLATE pg_catalog."default",
    payment_type character varying(20) COLLATE pg_catalog."default",
    check_number character varying(50) COLLATE pg_catalog."default",
    card_last4 character varying(4) COLLATE pg_catalog."default",
    z_id bigint,
    voided integer DEFAULT 0,
    void_date timestamp without time zone,
    voided_by character varying(50) COLLATE pg_catalog."default",
    register_id integer,
    CONSTRAINT sales_pkey PRIMARY KEY (sale_id)
)

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

CREATE TABLE IF NOT EXISTS public.z_reports
(
    z_id integer NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
    report_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    transaction_count integer,
    sales_total numeric(12,2),
    tax_total numeric(12,2),
    register_id integer,
    CONSTRAINT z_reports_pkey PRIMARY KEY (z_id)


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


