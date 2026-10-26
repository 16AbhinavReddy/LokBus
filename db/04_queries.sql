-- Average rating by bus
SELECT a.vehicle_number,COUNT(*) AS review_count,ROUND(AVG(r.rating),2) AS avg_rating
FROM reviews r JOIN service_assignments a USING(assignment_id)
GROUP BY a.vehicle_number ORDER BY avg_rating,review_count DESC;

-- Negative review count by driver
SELECT d.driver_id,d.driver_name,COUNT(*) AS negative_reviews
FROM reviews r JOIN service_assignments a USING(assignment_id)
JOIN drivers d USING(driver_id)
WHERE r.sentiment='Negative'
GROUP BY d.driver_id,d.driver_name ORDER BY negative_reviews DESC;

-- Most recent GPS record for each bus in the last hour
SELECT DISTINCT ON(l.vehicle_number) l.vehicle_number,rt.route_name,l.latitude,l.longitude,l.observed_at
FROM bus_locations l LEFT JOIN routes rt USING(route_id)
WHERE l.observed_at BETWEEN now()-interval '1 hour' AND now()
ORDER BY l.vehicle_number,l.observed_at DESC;

-- Import validation
SELECT 'buses' AS entity,COUNT(*) FROM buses UNION ALL SELECT 'routes',COUNT(*) FROM routes UNION ALL
SELECT 'assignments',COUNT(*) FROM service_assignments UNION ALL SELECT 'reviews',COUNT(*) FROM reviews;
SELECT COUNT(*) AS unmatched_reviews FROM reviews WHERE assignment_id IS NULL;
