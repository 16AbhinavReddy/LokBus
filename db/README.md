# LokBus database

Local PostgreSQL runs in Docker. From the repository root:

```bash
cd db
docker compose up -d
```

The database is available to your local app at `localhost:5432`:

The schema and staging tables are created on the database's first startup.

## Load the CSV data

Run the import script once from the `db` folder:

```bash
bash db-import.sh
```

The script copies the CSV files from `../data`, loads them into staging tables, runs `03_load.sql`, and prints row counts.

## Connect to PostgreSQL

```bash
docker exec -it lokbus-postgres psql -U lokbus -d lokbus
```
