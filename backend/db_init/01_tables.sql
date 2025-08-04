-- Создание таблицы cryptorank_upcoming
CREATE TABLE IF NOT EXISTS cryptorank_upcoming (
    id SERIAL PRIMARY KEY,
    row_index INTEGER,
    project_name VARCHAR(200),
    project_symbol VARCHAR(20),
    project_url VARCHAR(255),
    project_type VARCHAR(50),
    initial_cap VARCHAR(100),
    ido_raise VARCHAR(100),
    launch_date DATE,
    launch_date_original VARCHAR(50),
    moni_score VARCHAR(10),
    investors JSONB DEFAULT '[]',
    launchpad JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы cryptorank_tokenomics
CREATE TABLE IF NOT EXISTS cryptorank_tokenomics (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(200) UNIQUE,
    tokenomics JSONB,
    parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);