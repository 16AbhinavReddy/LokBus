import json
from pathlib import Path
import numpy as np
import pandas as pd

scraped_bus_data = Path("all_buses.json")
reviews_data = Path("bus_reviews.csv")
total_days = None

rng = np.random.default_rng(42)
reviews = pd.read_csv(reviews_data)
timestamps = pd.to_datetime(reviews["timestamp"], errors="coerce").dropna()
s_date = timestamps.min().normalize()
e_date = timestamps.max().normalize()

if total_days is not None:
    e_date = s_date + pd.Timedelta(days=total_days - 1)
with scraped_bus_data.open("r", encoding="utf-8") as f:
    bus_data = json.load(f)
rows = []
for key, val in bus_data.items():
    for obs in val.get("observations", []):
        veh_no = obs.get("vehicle_number", key)
        r_id = obs.get("route_id")
        r_name = obs.get("route_name")
        if r_id is None or r_name is None:
            continue
        rows.append({"vehicle_number": str(veh_no), "route_id": str(r_id),"route_name": str(r_name), "first_stop": obs.get("first_stop"), "last_stop": obs.get("last_stop"), "source_timestamp": obs.get("timestamp")})

data1 = pd.DataFrame(rows)
valid_pairs = (data1.drop_duplicates(subset=["vehicle_number", "route_id", "route_name",]).sort_values(["vehicle_number", "route_id"]).reset_index(drop=True))
valid_pairs.to_csv("valid_bus_route_pairs.csv", index=False)  # Logic ends for valid bus routes here

routes = {}
for key, val in valid_pairs.groupby("vehicle_number", sort=True):
    val = val.reset_index(drop=True)
    routes[str(key)] = val
vehicles = sorted(routes.keys())
driver_ids = []
for i in range(1, len(vehicles) + 1):
    id = f"D{i:03d}"
    driver_ids.append(id)
conductor_ids = []
for i in range(1, len(vehicles) + 1):
    id = f"C{i:03d}"
    conductor_ids.append(id)

dates = pd.date_range(s_date, e_date, freq="D")
mappings = []
for d in dates:
    veh = rng.permutation(vehicles)
    driver = rng.permutation(driver_ids)
    conductor = rng.permutation(conductor_ids)
    for i, vehicle in enumerate(veh):
        options = routes[vehicle]
        chosen = options.iloc[int(rng.integers(0, len(options)))]
        mappings.append({"service_date": d.strftime("%Y-%m-%d"), "vehicle_number": vehicle, "route_id": chosen["route_id"], "route_name": chosen["route_name"], "first_stop": chosen["first_stop"], "last_stop": chosen["last_stop"], "driver_id": driver[i], "conductor_id": conductor[i], "assignment_type": "synthetic"})

mappings = pd.DataFrame(mappings)
mappings = mappings.sort_values(["service_date", "vehicle_number"]).reset_index(drop=True)
mappings.to_csv("bus_route_driver_conductor_mapping.csv", index=False)   # Logic for mappings b/w diff bus objects

print(f"Saved valid_bus_route_pairs.csv: "f"{len(valid_pairs)} valid bus-route pairs")
print(f"Saved bus_route_driver_conductor_mapping.csv: {len(mappings)} assignments")
print(f"Date range: {s_date.date()} to {e_date.date()}")
print(f"Unique buses: {len(vehicles)}")
print(f"Drivers: {len(driver_ids)}")
print(f"Conductors: {len(conductor_ids)}")

