CREATE DATABASE iex_task_db;
use  iex_task_db;

create table user_accounts(
id int auto_increment primary key,
email varchar(100) unique not null,
hashed_password varchar(100) not null,
created_at timestamp default current_timestamp );

CREATE TABLE job_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_uuid VARCHAR(50),
    market_type VARCHAR(10),
    trade_date DATE,
    step_name VARCHAR(20),
    status VARCHAR(20),
    message TEXT,
    rows_inserted INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exchange_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE,
    market_type VARCHAR(10),
    block_no INT,
    `timestamp` DATETIME,
    buy_vol DECIMAL(18,2),
    mcv DECIMAL(18,2),
    mcp DECIMAL(18,2),
    sell_vol DECIMAL(18,2),
    area_code VARCHAR(20),
    job_uuid VARCHAR(50)
);

select * from user_accounts;
select * from exchange_data;
select * from job_logs;