import csv
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, render_template
from sqlalchemy import create_engine, text

root_dir = Path(__file__).resolve().parent.parent
analysis_dir = root_dir / "analysis"
output_dir = Path(__file__).resolve().parent / "generated"
db_url = os.getenv("ANALYTICS_db_url","postgresql+psycopg://lokbus:lokbus_dev@localhost:5432/lokbus")
report_config = {"Bus maintenance": ("bus_maintainence_analysis.py","bus_maintenance.csv"),"Driving": ("driving_analysis.py", "driving.csv"), "Crowding by route": ("crowding_analyis.py", "crowding.csv"), "Ticket handling": ("ticket_handling_analysis.py", "ticket_handling.csv")}

app = Flask(__name__)

def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))[:20]

def get_reports():
    report_data = {}
    for name, (_, output) in report_config.items():
        report_path = output_dir / output
        report_data[name] = read_csv(report_path)
    timestamp_path = output_dir / "refreshed_at.txt"
    if timestamp_path.exists():
        refreshed_at = timestamp_path.read_text(encoding="utf-8").strip()
    else:
        refreshed_at = None
    result = {"reports": report_data, "refreshed_at": refreshed_at}
    return result

def refresh_reports():
    output_dir.mkdir(parents=True, exist_ok=True)
    source = output_dir / "reviews.csv"
    mapping_path = (root_dir / "data" / "bus_route_driver_conductor_mapping_with_names.csv")
    with mapping_path.open(newline="", encoding="utf-8") as mapping_file:
        mappings = list(csv.DictReader(mapping_file))

    drivers = {}
    for row in mappings:
        if row.get("driver_id") and row.get("driver_name"):
            drivers[row["driver_id"]] = row["driver_name"]

    conductors = {}
    for row in mappings:
        if row.get("conductor_id") and row.get("conductor_name"):
            conductors[row["conductor_id"]] = row["conductor_name"]

    query_path = (Path(__file__).resolve().parent / "queries" / "reviews.sql")
    query = text(query_path.read_text(encoding="utf-8"))
    engine = create_engine(db_url)

    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            cols = list(result.keys())
            rows = result.fetchall()
            with source.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(cols)
                d_idx = cols.index("driver_name")
                did_idx = cols.index("driver_id")
                c_idx = cols.index("conductor_name")
                cid_idx = cols.index("conductor_id")
                for row in rows:
                    values = list(row)
                    if not values[d_idx]:
                        values[d_idx] = drivers.get(values[did_idx], "")
                    if not values[c_idx]:
                        values[c_idx] = conductors.get(values[cid_idx], "")
                    writer.writerow(values)
    finally:
        engine.dispose()

    for script, output in report_config.values():
        script_path = analysis_dir / script
        output_path = output_dir / output
        subprocess.run([sys.executable, str(script_path), "--input", str(source), "--output", str(output_path)], cwd=str(analysis_dir),check=True,timeout=180)
    (output_dir / "refreshed_at.txt").write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/reports")
def api_reports():
    result = get_reports()
    return jsonify(result)

@app.post("/api/refresh")
def api_refresh():
    try:
        refresh_reports()
        return jsonify(get_reports())
    except Exception:
        app.logger.exception("Analytics refresh failed")
        return jsonify({"error": ("Refresh failed. Check the PostgreSQL connection, SQL query, analysis scripts, and server log.")}), 500

if __name__ == "__main__":
    app.run(port=5050, debug=False)