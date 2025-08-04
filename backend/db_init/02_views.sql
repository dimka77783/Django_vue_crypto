-- Удаляем все существующие вьюшки
DROP VIEW IF EXISTS tokenomics_detailed CASCADE;
DROP VIEW IF EXISTS tokenomics_summary CASCADE;
DROP VIEW IF EXISTS crypto_issues CASCADE;
DROP VIEW IF EXISTS crypto_without_social CASCADE;
DROP VIEW IF EXISTS active_telegram_channels CASCADE;
DROP VIEW IF EXISTS telegram_stats CASCADE;
DROP VIEW IF EXISTS crypto_social_links CASCADE;
DROP VIEW IF EXISTS upcoming_soon CASCADE;
DROP VIEW IF EXISTS upcoming_projects_stats CASCADE;
DROP VIEW IF EXISTS crypto_stats CASCADE;

-- Представление: ближайшие запуски
CREATE OR REPLACE VIEW upcoming_soon AS
SELECT
    project_name,
    project_symbol,
    project_type,
    initial_cap,
    ido_raise,
    launch_date,
    moni_score,
    EXTRACT(EPOCH FROM (launch_date::timestamp - CURRENT_TIMESTAMP))/86400 as days_until_launch
FROM cryptorank_upcoming
WHERE is_active = TRUE
  AND launch_date IS NOT NULL
  AND launch_date >= CURRENT_DATE
  AND launch_date <= CURRENT_DATE + INTERVAL '30 days'
ORDER BY launch_date ASC;

-- Представление: детальная токеномика
CREATE OR REPLACE VIEW tokenomics_detailed AS
SELECT
    t.project_name,
    t.parsed_at,
    t.tokenomics->'distribution' as distribution_data,
    t.tokenomics->'initial_values'->>'Total supply' as total_supply,
    t.tokenomics->'initial_values'->>'Circulating supply' as circulating_supply,
    t.tokenomics->'initial_values'->>'Max supply' as max_supply,
    t.tokenomics->'initial_values'->>'Initial price' as initial_price,
    t.tokenomics->'initial_values'->>'Market cap' as market_cap,
    (SELECT COUNT(*) FROM jsonb_object_keys(COALESCE(t.tokenomics->'distribution', '{}'::jsonb))) as categories_count,
    CASE
        WHEN (SELECT COUNT(*) FROM jsonb_object_keys(COALESCE(t.tokenomics->'distribution', '{}'::jsonb))) > 0 THEN 'Complete'
        WHEN t.tokenomics->'initial_values' IS NOT NULL THEN 'Partial'
        ELSE 'Minimal'
    END as data_quality
FROM cryptorank_tokenomics t
ORDER BY t.parsed_at DESC;

-- Представление: социальные ссылки
CREATE OR REPLACE VIEW crypto_social_links AS
SELECT
    c.id,
    c.project_symbol as symbol,
    c.project_name as name,
    c.investors,
    c.launchpad,
    CASE
        WHEN c.investors IS NOT NULL THEN jsonb_array_length(c.investors)
        ELSE 0
    END +
    CASE
        WHEN c.launchpad IS NOT NULL THEN jsonb_array_length(c.launchpad)
        ELSE 0
    END as total_links
FROM cryptorank_upcoming c
ORDER BY total_links DESC;