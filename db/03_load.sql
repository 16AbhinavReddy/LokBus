-- Run AFTER loading the CSVs into staging with psql \copy (see README).
BEGIN;
ALTER TABLE reviews
    ADD COLUMN IF NOT EXISTS category TEXT,
    ADD COLUMN IF NOT EXISTS scenario TEXT,
    ADD COLUMN IF NOT EXISTS route TEXT,
    ADD COLUMN IF NOT EXISTS "timestamp" TEXT,
    ADD COLUMN IF NOT EXISTS review TEXT,
    ADD COLUMN IF NOT EXISTS service_date TEXT,
    ADD COLUMN IF NOT EXISTS assigned_vehicle_number TEXT,
    ADD COLUMN IF NOT EXISTS assigned_route_id TEXT,
    ADD COLUMN IF NOT EXISTS assigned_route_name TEXT,
    ADD COLUMN IF NOT EXISTS assigned_first_stop TEXT,
    ADD COLUMN IF NOT EXISTS assigned_last_stop TEXT,
    ADD COLUMN IF NOT EXISTS driver_id TEXT,
    ADD COLUMN IF NOT EXISTS conductor_id TEXT,
    ADD COLUMN IF NOT EXISTS assignment_type TEXT,
    ADD COLUMN IF NOT EXISTS is_negative TEXT,
    ADD COLUMN IF NOT EXISTS negative_count TEXT;
INSERT INTO buses(vehicle_number)
SELECT DISTINCT vehicle_number FROM (
 SELECT vehicle_number FROM stg_bus_route_pairs UNION ALL SELECT vehicle_number FROM stg_assignments UNION ALL SELECT assigned_vehicle_number FROM stg_reviews
) x WHERE NULLIF(trim(vehicle_number),'') IS NOT NULL ON CONFLICT DO NOTHING;

INSERT INTO routes(route_id,route_name,first_stop,last_stop)
SELECT DISTINCT ON(route_id) route_id,route_name,first_stop,last_stop FROM (
 SELECT route_id,route_name,first_stop,last_stop,1 AS priority FROM stg_bus_route_pairs
 UNION ALL SELECT route_id,route_name,first_stop,last_stop,2 FROM stg_assignments
 UNION ALL SELECT assigned_route_id,assigned_route_name,assigned_first_stop,assigned_last_stop,3 FROM stg_reviews
) x WHERE NULLIF(trim(route_id),'') IS NOT NULL ORDER BY route_id,priority
ON CONFLICT(route_id) DO NOTHING;

INSERT INTO bus_route_pairs(vehicle_number,route_id,source_timestamp)
SELECT vehicle_number,route_id, CASE WHEN source_timestamp ~ '^[0-9]{13}$' THEN to_timestamp(source_timestamp::double precision/1000) ELSE NULL END
FROM stg_bus_route_pairs WHERE vehicle_number IS NOT NULL AND route_id IS NOT NULL
ON CONFLICT(vehicle_number,route_id) DO NOTHING;

INSERT INTO drivers(driver_id,driver_name)
SELECT DISTINCT ON(driver_id) driver_id,driver_name FROM stg_assignments WHERE NULLIF(trim(driver_id),'') IS NOT NULL ORDER BY driver_id,driver_name NULLS LAST
ON CONFLICT(driver_id) DO NOTHING;
INSERT INTO conductors(conductor_id,conductor_name)
SELECT DISTINCT ON(conductor_id) conductor_id,conductor_name FROM stg_assignments WHERE NULLIF(trim(conductor_id),'') IS NOT NULL ORDER BY conductor_id,conductor_name NULLS LAST
ON CONFLICT(conductor_id) DO NOTHING;

INSERT INTO service_assignments(service_date,vehicle_number,route_id,driver_id,conductor_id,assignment_type)
SELECT DISTINCT ON(service_date,vehicle_number) service_date::date,vehicle_number,route_id,driver_id,conductor_id,assignment_type
FROM stg_assignments WHERE service_date IS NOT NULL AND vehicle_number IS NOT NULL AND route_id IS NOT NULL
ORDER BY service_date,vehicle_number,route_id
ON CONFLICT(service_date,vehicle_number) DO NOTHING;

INSERT INTO review_categories(category_name)
SELECT DISTINCT category FROM stg_reviews WHERE NULLIF(trim(category),'') IS NOT NULL ON CONFLICT DO NOTHING;
INSERT INTO review_scenarios(category_id,scenario_name)
SELECT DISTINCT c.category_id,r.scenario FROM stg_reviews r JOIN review_categories c ON c.category_name=r.category
WHERE NULLIF(trim(r.scenario),'') IS NOT NULL ON CONFLICT DO NOTHING;

-- Reviews that cannot match an assignment are kept with assignment_id NULL.
INSERT INTO reviews (review_id, assignment_id, scenario_id, review_text, rating,
    sentiment, severity, reviewed_at, time_of_day, source_route_label, source_dataset, original_review_id, source_is_negative, source_negative_count, category,
    scenario, route, "timestamp", review, service_date, assigned_vehicle_number,
    assigned_route_id, assigned_route_name, assigned_first_stop, assigned_last_stop, driver_id, conductor_id, assignment_type, is_negative, negative_count)
SELECT DISTINCT ON (r.review_id)
    r.review_id::bigint, a.assignment_id, s.scenario_id, r.review, NULLIF(r.rating, '')::smallint, r.sentiment, r.severity, r."timestamp"::timestamp, r.time_of_day, r.route, r.source_dataset, NULLIF(r.original_review_id, '')::bigint, NULLIF(r.is_negative, '')::boolean, NULLIF(r.negative_count, '')::numeric, r.category,
    r.scenario, r.route, r."timestamp", r.review, r.service_date, r.assigned_vehicle_number, r.assigned_route_id, r.assigned_route_name, r.assigned_first_stop,
    r.assigned_last_stop, r.driver_id, r.conductor_id, r.assignment_type, r.is_negative, r.negative_count
FROM stg_reviews r JOIN review_categories c ON c.category_name = r.category
JOIN review_scenarios s ON s.category_id = c.category_id AND s.scenario_name = r.scenario LEFT JOIN service_assignments a ON a.service_date = r.service_date::date AND a.vehicle_number = r.assigned_vehicle_number AND a.route_id = r.assigned_route_id WHERE r.review_id ~ '^[0-9]+$' AND NULLIF(r.review, '') IS NOT NULL AND NULLIF(r."timestamp", '') IS NOT NULL 
ORDER BY r.review_id, a.assignment_id NULLS LAST ON CONFLICT (review_id) DO UPDATE SET category = EXCLUDED.category, scenario = EXCLUDED.scenario, route = EXCLUDED.route, "timestamp" = EXCLUDED."timestamp", review = EXCLUDED.review, service_date = EXCLUDED.service_date, assigned_vehicle_number = EXCLUDED.assigned_vehicle_number, assigned_route_id = EXCLUDED.assigned_route_id, assigned_route_name = EXCLUDED.assigned_route_name, assigned_first_stop = EXCLUDED.assigned_first_stop, assigned_last_stop = EXCLUDED.assigned_last_stop, driver_id = EXCLUDED.driver_id, conductor_id = EXCLUDED.conductor_id, assignment_type = EXCLUDED.assignment_type, is_negative = EXCLUDED.is_negative, negative_count = EXCLUDED.negative_count;
COMMIT;
