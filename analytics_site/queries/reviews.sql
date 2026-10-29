SELECT c.category_name AS category, r.sentiment,
       a.vehicle_number AS assigned_vehicle_number,
       a.route_id AS assigned_route_id, rt.route_name AS assigned_route_name,
       a.conductor_id, cnd.conductor_name,
       a.driver_id, d.driver_name
FROM reviews r
JOIN review_scenarios s ON s.scenario_id = r.scenario_id
JOIN review_categories c ON c.category_id = s.category_id
LEFT JOIN service_assignments a ON a.assignment_id = r.assignment_id
LEFT JOIN routes rt ON rt.route_id = a.route_id
LEFT JOIN drivers d ON d.driver_id = a.driver_id
LEFT JOIN conductors cnd ON cnd.conductor_id = a.conductor_id
ORDER BY r.review_id