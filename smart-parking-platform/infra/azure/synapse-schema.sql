-- ============================================================
-- Azure Synapse Analytics — Star Schema for Smart Parking
-- ============================================================
-- Data Warehousing Theory:
-- Star schema optimizes analytical queries via denormalization.
-- Fact tables store events/measurements; dimension tables provide context.
-- ============================================================

-- ─── Dimension Tables ─────────────────────────────────────

CREATE TABLE dim_zone (
    zone_key        INT IDENTITY(1,1) PRIMARY KEY,
    zone_code       VARCHAR(20) NOT NULL,
    zone_name       VARCHAR(100),
    zone_type       VARCHAR(30),
    floor_level     INT,
    total_spots     INT,
    hourly_rate     DECIMAL(6,2),
    latitude        DECIMAL(10,7),
    longitude       DECIMAL(10,7),
    effective_from  DATETIME2 DEFAULT GETUTCDATE(),
    effective_to    DATETIME2 DEFAULT '9999-12-31',
    is_current      BIT DEFAULT 1
);

CREATE TABLE dim_time (
    time_key        INT PRIMARY KEY,  -- YYYYMMDDHH format
    full_datetime   DATETIME2 NOT NULL,
    date_value      DATE NOT NULL,
    year            INT,
    quarter         INT,
    month           INT,
    month_name      VARCHAR(20),
    week            INT,
    day_of_week     INT,
    day_name        VARCHAR(20),
    hour            INT,
    is_weekend      BIT,
    is_peak_hour    BIT  -- 9-11, 17-19
);

CREATE TABLE dim_vehicle_type (
    vehicle_type_key  INT IDENTITY(1,1) PRIMARY KEY,
    vehicle_type      VARCHAR(30) NOT NULL,
    category          VARCHAR(30),  -- compact, standard, oversized
    avg_space_needed  DECIMAL(3,1)  -- in standard spot units
);

CREATE TABLE dim_camera (
    camera_key      INT IDENTITY(1,1) PRIMARY KEY,
    camera_id       VARCHAR(50) NOT NULL,
    camera_name     VARCHAR(100),
    zone_code       VARCHAR(20),
    resolution      VARCHAR(20),
    is_active       BIT DEFAULT 1
);

-- ─── Fact Tables ──────────────────────────────────────────

CREATE TABLE fact_parking_events (
    event_id            BIGINT IDENTITY(1,1) PRIMARY KEY,
    zone_key            INT REFERENCES dim_zone(zone_key),
    time_key            INT REFERENCES dim_time(time_key),
    vehicle_type_key    INT REFERENCES dim_vehicle_type(vehicle_type_key),
    camera_key          INT REFERENCES dim_camera(camera_key),
    event_type          VARCHAR(10) NOT NULL,  -- entry / exit
    license_plate       VARCHAR(20),
    confidence_score    DECIMAL(5,4),
    duration_minutes    INT,  -- NULL for entries, computed for exits
    revenue             DECIMAL(8,2)
);

CREATE TABLE fact_occupancy (
    snapshot_id         BIGINT IDENTITY(1,1) PRIMARY KEY,
    zone_key            INT REFERENCES dim_zone(zone_key),
    time_key            INT REFERENCES dim_time(time_key),
    occupied_spots      INT NOT NULL,
    total_spots         INT NOT NULL,
    occupancy_rate      DECIMAL(5,2) NOT NULL,
    vehicle_count_car   INT DEFAULT 0,
    vehicle_count_truck INT DEFAULT 0,
    vehicle_count_moto  INT DEFAULT 0
);

-- ─── Indexes for Query Performance ────────────────────────

CREATE INDEX idx_fact_events_time ON fact_parking_events(time_key);
CREATE INDEX idx_fact_events_zone ON fact_parking_events(zone_key);
CREATE INDEX idx_fact_occupancy_time ON fact_occupancy(time_key);
CREATE INDEX idx_fact_occupancy_zone ON fact_occupancy(zone_key);

-- ─── Staging Table (for ADF loads) ────────────────────────

CREATE SCHEMA staging;

CREATE TABLE staging.fact_parking_events (
    zone_code           VARCHAR(20),
    event_type          VARCHAR(10),
    vehicle_type        VARCHAR(30),
    license_plate       VARCHAR(20),
    confidence_score    DECIMAL(5,4),
    camera_id           VARCHAR(50),
    event_timestamp     DATETIME2
);

-- ─── Sample Analytical Queries ────────────────────────────

-- Hourly occupancy trend for a zone (last 7 days)
-- SELECT t.hour, AVG(f.occupancy_rate) AS avg_rate
-- FROM fact_occupancy f
-- JOIN dim_time t ON f.time_key = t.time_key
-- JOIN dim_zone z ON f.zone_key = z.zone_key
-- WHERE z.zone_code = 'A1'
--   AND t.date_value >= DATEADD(DAY, -7, GETUTCDATE())
-- GROUP BY t.hour
-- ORDER BY t.hour;

-- Revenue by zone and day
-- SELECT z.zone_name, t.date_value, SUM(f.revenue) AS daily_revenue
-- FROM fact_parking_events f
-- JOIN dim_zone z ON f.zone_key = z.zone_key
-- JOIN dim_time t ON f.time_key = t.time_key
-- GROUP BY z.zone_name, t.date_value
-- ORDER BY t.date_value DESC, daily_revenue DESC;
