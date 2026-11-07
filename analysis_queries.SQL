


USE urban_pulse_db;

-- =========================================================
-- 1. Total distinct request volume
-- =========================================================
SELECT COUNT(DISTINCT unique_key) AS total_distinct_requests
FROM service_requests;



-- =========================================================
-- 2. Top 10 complaint categories
-- =========================================================
SELECT
    complaint_type,
    COUNT(*) AS request_count
FROM service_requests
GROUP BY complaint_type
ORDER BY request_count DESC, complaint_type
LIMIT 10;

SELECT
    MIN(complaint_type) AS category_label,
    COUNT(*) AS request_count
FROM service_requests
WHERE LOWER(complaint_type) = 'plumbing'
GROUP BY BINARY complaint_type;

ALTER TABLE service_requests
MODIFY COLUMN complaint_type TEXT
CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
-- final --
SELECT complaint_type, COUNT(*) AS request_count
FROM service_requests
GROUP BY complaint_type
ORDER BY request_count DESC, complaint_type
LIMIT 10;


-- =========================================================
-- 3. Agency workload distribution
-- =========================================================
SELECT
    agency,
    COUNT(*) AS request_count,
    ROUND(
        100.0 * COUNT(*) /
        (SELECT COUNT(*) FROM service_requests), 2
    ) AS sample_percentage
FROM service_requests
GROUP BY agency
ORDER BY request_count DESC;


-- =========================================================
-- 4. Request volume by borough
-- =========================================================
SELECT
    borough,
    COUNT(*) AS request_count
FROM service_requests
GROUP BY borough
ORDER BY request_count DESC;


-- =========================================================
-- 5. Monthly request trend - SAMPLE COUNTS
-- Full API monthly totals are saved in monthly_counts.csv.
-- Sample sizes were deliberately allocated across months.
-- =========================================================
SELECT
    DATE_FORMAT(created_date, '%Y-%m') AS creation_month,
    COUNT(*) AS sampled_requests
FROM service_requests
GROUP BY DATE_FORMAT(created_date, '%Y-%m')
ORDER BY creation_month;


-- =========================================================
-- 6. Demand by weekday and hour
-- WEEKDAY(): Monday = 0, Sunday = 6.
-- Recorded hours are used without timezone conversion.
-- =========================================================
SELECT
    WEEKDAY(created_date) AS weekday_number,
    DAYNAME(created_date) AS weekday_name,
    HOUR(created_date) AS creation_hour,
    COUNT(*) AS request_count
FROM service_requests
WHERE created_date IS NOT NULL
GROUP BY
    WEEKDAY(created_date),
    DAYNAME(created_date),
    HOUR(created_date)
ORDER BY weekday_number, creation_hour;


-- =========================================================
-- 7. Distribution of recorded request statuses
-- =========================================================

SELECT
    status,
    COUNT(*) AS request_count
FROM service_requests
GROUP BY status
ORDER BY request_count DESC;


-- =========================================================
-- Prepare valid durations for Tasks 8, 11 and 12.
-- Negative/invalid durations were excluded during cleaning.
-- =========================================================
DROP TEMPORARY TABLE IF EXISTS resolution_ranked;

CREATE TEMPORARY TABLE resolution_ranked AS
SELECT
    unique_key,
    resolution_hours,
    ROW_NUMBER() OVER (
        ORDER BY resolution_hours, unique_key
    ) AS rn
FROM service_requests
WHERE resolution_hours IS NOT NULL
  AND resolution_hours >= 0;

SELECT COUNT(*) INTO @duration_n
FROM resolution_ranked;





-- =========================================================
-- 8. Descriptive statistics for valid resolution durations
-- Variance and standard deviation use sample formulas.
-- =========================================================

-- 1
SELECT
    COUNT(*) AS valid_duration_count,
    AVG(resolution_hours) AS mean_hours,
    MIN(resolution_hours) AS minimum_hours,
    MAX(resolution_hours) AS maximum_hours,
    MAX(resolution_hours) - MIN(resolution_hours) AS range_hours,
    VAR_SAMP(resolution_hours) AS sample_variance,
    STDDEV_SAMP(resolution_hours) AS sample_standard_deviation
FROM service_requests
WHERE resolution_hours IS NOT NULL
  AND resolution_hours >= 0;
  
  -- 2
  WITH ranked AS (
    SELECT
        resolution_hours,
        ROW_NUMBER() OVER (
            ORDER BY resolution_hours, unique_key
        ) AS rn,
        COUNT(*) OVER () AS total
    FROM service_requests
    WHERE resolution_hours IS NOT NULL
      AND resolution_hours >= 0
)
SELECT AVG(resolution_hours) AS median_hours
FROM ranked
WHERE rn IN (
    FLOOR((total + 1) / 2),
    FLOOR((total + 2) / 2)
);

-- 3
WITH ranked AS (
    SELECT
        resolution_hours,
        ROW_NUMBER() OVER (
            ORDER BY resolution_hours, unique_key
        ) AS rn,
        COUNT(*) OVER () AS n
    FROM service_requests
    WHERE resolution_hours IS NOT NULL
      AND resolution_hours >= 0
),
positions AS (
    SELECT 'Q1' AS quartile, 0.25 AS fraction
    UNION ALL
    SELECT 'Q3', 0.75
),
endpoints AS (
    SELECT
        p.quartile,
        1 + (r.n - 1) * p.fraction AS position,
        MAX(CASE
            WHEN r.rn = FLOOR(1 + (r.n - 1) * p.fraction)
            THEN r.resolution_hours
        END) AS lower_value,
        MAX(CASE
            WHEN r.rn = CEIL(1 + (r.n - 1) * p.fraction)
            THEN r.resolution_hours
        END) AS upper_value
    FROM ranked r
    CROSS JOIN positions p
    GROUP BY p.quartile, p.fraction, r.n
)
SELECT
    quartile,
    lower_value
        + (position - FLOOR(position))
        * (upper_value - lower_value) AS hours
FROM endpoints
ORDER BY quartile;


-- =========================================================
-- 9. Median resolution duration by complaint category
-- Includes total volume and valid-duration count.
-- =========================================================
WITH ranked AS (
    SELECT
        complaint_type,
        resolution_hours,
        ROW_NUMBER() OVER (
            PARTITION BY complaint_type
            ORDER BY resolution_hours, unique_key
        ) AS rn,
        COUNT(*) OVER (
            PARTITION BY complaint_type
        ) AS n
    FROM service_requests
    WHERE resolution_hours IS NOT NULL
      AND resolution_hours >= 0
)
SELECT
    complaint_type,
    MAX(n) AS valid_duration_count,
    AVG(resolution_hours) AS median_hours
FROM ranked
WHERE rn IN (
    FLOOR((n + 1) / 2),
    FLOOR((n + 2) / 2)
)
GROUP BY complaint_type
ORDER BY median_hours DESC, complaint_type
LIMIT 10;

-- =========================================================
-- 10. Median resolution duration by agency
-- Agencies without valid durations retain a NULL median.
-- =========================================================
WITH ranked AS (
    SELECT
        agency,
        resolution_hours,
        ROW_NUMBER() OVER (
            PARTITION BY agency
            ORDER BY resolution_hours, unique_key
        ) AS rn,
        COUNT(*) OVER (PARTITION BY agency) AS n
    FROM service_requests
    WHERE resolution_hours IS NOT NULL
      AND resolution_hours >= 0
),
medians AS (
    SELECT
        agency,
        MAX(n) AS valid_duration_count,
        AVG(resolution_hours) AS median_hours
    FROM ranked
    WHERE rn IN (FLOOR((n + 1) / 2), FLOOR((n + 2) / 2))
    GROUP BY agency
),
volumes AS (
    SELECT agency, COUNT(*) AS request_count
    FROM service_requests
    GROUP BY agency
)
SELECT
    v.agency,
    v.request_count,
    COALESCE(m.valid_duration_count, 0) AS valid_duration_count,
    m.median_hours
FROM volumes v
LEFT JOIN medians m ON v.agency <=> m.agency
ORDER BY m.median_hours DESC;


-- =========================================================
-- 11. IQR-based outlier investigation
-- Run the quantile preparation above first.
-- =========================================================
SET @q1 = 1.073888888888889;
SET @q3 = 78.23388888888888;
SET @iqr = @q3 - @q1;
SET @lower_bound = @q1 - 1.5 * @iqr;
SET @upper_bound = @q3 + 1.5 * @iqr;

SELECT
    @iqr AS iqr,
    @lower_bound AS lower_boundary,
    @upper_bound AS upper_boundary;
    
SELECT COUNT(*) AS flagged_durations
FROM service_requests
WHERE resolution_hours IS NOT NULL
  AND resolution_hours >= 0
  AND (
      resolution_hours < @lower_bound
      OR resolution_hours > @upper_bound
  );
  
  
  SELECT
    unique_key,
    agency,
    complaint_type,
    created_date,
    closed_date,
    resolution_hours
FROM service_requests
WHERE resolution_hours >= 0
  AND (
      resolution_hours < @lower_bound
      OR resolution_hours > @upper_bound
  )
ORDER BY resolution_hours DESC, unique_key
LIMIT 10;
    
-- =========================================================
-- 12. Resolution-time skewness and distribution
-- Adjusted sample skewness, comparable with Pandas .skew().
-- Histogram and boxplot are produced in Python.
-- =========================================================
WITH valid AS (
    SELECT resolution_hours
    FROM service_requests
    WHERE resolution_hours IS NOT NULL
      AND resolution_hours >= 0
),
summary AS (
    SELECT COUNT(*) AS n, AVG(resolution_hours) AS mean_hours
    FROM valid
),
moments AS (
    SELECT
        s.n,
        AVG(POWER(v.resolution_hours - s.mean_hours, 2)) AS m2,
        AVG(POWER(v.resolution_hours - s.mean_hours, 3)) AS m3
    FROM valid v
    CROSS JOIN summary s
    GROUP BY s.n
)
SELECT
    CASE
        WHEN n > 2 AND m2 > 0
        THEN SQRT(n * (n - 1.0)) / (n - 2.0)
             * m3 / POWER(m2, 1.5)
    END AS skewness
FROM moments;
-- =========================================================
-- 13. Geographic concentration - borough summary
-- These are sample shares, not population-adjusted rates.
-- =========================================================
SELECT
    borough,
    COUNT(*) AS request_count,
    ROUND(
        100.0 * COUNT(*) /
        (SELECT COUNT(*) FROM service_requests), 2
    ) AS sample_percentage
FROM service_requests
GROUP BY borough
ORDER BY request_count DESC;


-- =========================================================
-- 14. Recorded closure-rate comparison by borough
-- is_closed was derived from presence of a closure date.
-- =========================================================
SELECT
    borough,
    COUNT(*) AS total_requests,
    SUM(CASE WHEN is_closed = 1 THEN 1 ELSE 0 END)
        AS recorded_closed,
    ROUND(
        100.0
        * SUM(CASE WHEN is_closed = 1 THEN 1 ELSE 0 END)
        / COUNT(*), 2
    ) AS closure_rate_percent
FROM service_requests
GROUP BY borough
ORDER BY closure_rate_percent DESC;


-- =========================================================
-- 15. High volume and long median resolution duration
-- Eligible categories: at least 30 valid durations.
-- Calculate their metrics, then interpolated P75 thresholds.
-- =========================================================
WITH ranked AS (
    SELECT
        complaint_type,
        resolution_hours,
        ROW_NUMBER() OVER (
            PARTITION BY complaint_type
            ORDER BY resolution_hours, unique_key
        ) AS rn,
        COUNT(*) OVER (
            PARTITION BY complaint_type
        ) AS n
    FROM service_requests
    WHERE resolution_hours IS NOT NULL
      AND resolution_hours >= 0
),
medians AS (
    SELECT
        complaint_type,
        MAX(n) AS valid_duration_count,
        AVG(resolution_hours) AS median_hours
    FROM ranked
    WHERE rn IN (
        FLOOR((n + 1) / 2),
        FLOOR((n + 2) / 2)
    )
    GROUP BY complaint_type
),
volumes AS (
    SELECT
        complaint_type,
        COUNT(DISTINCT unique_key) AS request_count
    FROM service_requests
    GROUP BY complaint_type
)
SELECT
    v.complaint_type,
    v.request_count,
    m.valid_duration_count,
    m.median_hours
FROM volumes v
JOIN medians m
    ON v.complaint_type = m.complaint_type
WHERE m.valid_duration_count >= 30
  AND v.request_count >= 888.5
  AND m.median_hours >= 216.85631944444444
ORDER BY v.request_count DESC;