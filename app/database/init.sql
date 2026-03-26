-- 1. Create user (if not )
CREATE ROLE :DB_USERNAME LOGIN PASSWORD :'DB_PASSWORD';

-- 2. Create database
CREATE DATABASE :DB_NAME OWNER :DB_USERNAME;

-- 3. Connect to the database
\connect :DB_NAME :DB_USERNAME :DB_HOST;

-- 4. Grant privileges on database
GRANT ALL PRIVILEGES ON DATABASE :DB_NAME TO :DB_USERNAME;

-- 5. Grant schema permissions
GRANT ALL ON SCHEMA public TO :DB_USERNAME;

-- 6. Create table
CREATE TABLE IF NOT EXISTS reports (
    identifier VARCHAR PRIMARY KEY,
    identifier_type INTEGER DEFAULT 1,
    data JSONB
);

-- 7. Ensure ownership
ALTER TABLE reports OWNER TO :DB_USERNAME;