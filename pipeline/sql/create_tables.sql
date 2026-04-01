CREATE TABLE IF NOT EXISTS hourly_aggregations (
    id        SERIAL PRIMARY KEY,
    location  TEXT NOT NULL,
    hour      TIMESTAMP NOT NULL,
    date      DATE NOT NULL,
    total_in  INTEGER NOT NULL,
    total_out INTEGER NOT NULL,
    net_flow  INTEGER NOT NULL,
    occupancy INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_aggregations (
    id        SERIAL PRIMARY KEY,
    location  TEXT NOT NULL,
    date      DATE NOT NULL,
    total_in  INTEGER NOT NULL,
    total_out INTEGER NOT NULL,
    net_flow  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hourly_location_date ON hourly_aggregations (location, date);
CREATE INDEX IF NOT EXISTS idx_daily_location_date ON daily_aggregations (location, date);
