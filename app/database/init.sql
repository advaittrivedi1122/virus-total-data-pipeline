GRANT ALL ON SCHEMA public TO db_user;

CREATE DATABASE virus_total OWNER db_user;

\connect virus_total;

GRANT ALL PRIVILEGES ON DATABASE virus_total TO db_user;

CREATE TABLE IF NOT EXISTS reports (
    identifier VARCHAR PRIMARY KEY,
    identifier_type INTEGER DEFAULT 1,
    data JSONB
);

ALTER TABLE reports OWNER TO db_user;