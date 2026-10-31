#!/bin/bash

docker compose up -d
sleep 10
docker exec lokbus-postgres pg_isready -U lokbus -d lokbus
docker exec -i lokbus-postgres psql -U lokbus -d lokbus -v ON_ERROR_STOP=1 < 01_schema.sql
docker exec -i lokbus-postgres psql -U lokbus -d lokbus -v ON_ERROR_STOP=1 < 02_staging.sql
docker cp ../data/valid_bus_route_pairs.csv lokbus-postgres:/tmp/pairs.csv
docker cp ../data/bus_route_driver_conductor_mapping_with_names.csv lokbus-postgres:/tmp/assignments.csv
docker cp ../data/bus_reviews_merged.csv lokbus-postgres:/tmp/reviews.csv

docker exec -i lokbus-postgres psql -U lokbus -d lokbus -v ON_ERROR_STOP=1 -c "\copy stg_bus_route_pairs FROM '/tmp/pairs.csv' WITH (FORMAT csv, HEADER true)" -c "\copy stg_assignments FROM '/tmp/assignments.csv' WITH (FORMAT csv, HEADER true)" -c "\copy stg_reviews FROM '/tmp/reviews.csv' WITH (FORMAT csv, HEADER true)"

docker exec -i lokbus-postgres psql -U lokbus -d lokbus -v ON_ERROR_STOP=1 < 03_load.sql
docker exec -i lokbus-postgres psql -U lokbus -d lokbus -v ON_ERROR_STOP=1 < 06_identity_review_ratings.sql

docker exec -it lokbus-postgres psql -U lokbus -d lokbus -c "SELECT 'buses' AS table_name, COUNT(*) FROM buses UNION ALL SELECT 'routes', COUNT(*) FROM routes UNION ALL SELECT 'reviews', COUNT(*) FROM reviews;"
