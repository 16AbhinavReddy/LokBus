CREATE INDEX IF NOT EXISTS idx_assignments_vehicle ON service_assignments(vehicle_number);
CREATE INDEX IF NOT EXISTS idx_assignments_driver ON service_assignments(driver_id);
CREATE INDEX IF NOT EXISTS idx_assignments_conductor ON service_assignments(conductor_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating) WHERE rating IS NOT NULL;

CREATE OR REPLACE VIEW bus_average_ratings AS
SELECT b.vehicle_number, COUNT(r.rating)::bigint AS rated_review_count, ROUND(AVG(r.rating)::numeric, 2) AS average_rating FROM buses AS b LEFT JOIN service_assignments AS a ON a.vehicle_number = b.vehicle_number LEFT JOIN reviews AS r ON r.assignment_id = a.assignment_id AND r.rating IS NOT NULL GROUP BY b.vehicle_number;

CREATE OR REPLACE VIEW driver_average_ratings AS
SELECT d.driver_id, d.driver_name, COUNT(r.rating)::bigint AS rated_review_count, ROUND(AVG(r.rating)::numeric, 2) AS average_rating FROM drivers AS d LEFT JOIN service_assignments AS a ON a.driver_id = d.driver_id LEFT JOIN reviews AS r ON r.assignment_id = a.assignment_id AND r.rating IS NOT NULL GROUP BY d.driver_id, d.driver_name;

CREATE OR REPLACE VIEW conductor_average_ratings AS SELECT c.conductor_id, c.conductor_name, COUNT(r.rating)::bigint AS rated_review_count, ROUND(AVG(r.rating)::numeric, 2) AS average_rating FROM conductors AS c LEFT JOIN service_assignments AS a ON a.conductor_id = c.conductor_id LEFT JOIN reviews AS r ON r.assignment_id = a.assignment_id AND r.rating IS NOT NULL GROUP BY c.conductor_id, c.conductor_name;

SELECT * FROM bus_average_ratings ORDER BY vehicle_number;
SELECT * FROM driver_average_ratings ORDER BY driver_id;
SELECT * FROM conductor_average_ratings ORDER BY conductor_id;
