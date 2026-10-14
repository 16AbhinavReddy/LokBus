
from pathlib import Path
import numpy as np
import pandas as pd

file1 = Path("bus_reviews.csv")
file2 = Path("valid_bus_route_pairs.csv")
file3 = Path("bus_route_driver_conductor_mapping.csv")
output = Path("bus_reviews_enriched1.csv")

reviews = pd.read_csv(file1)
valid_pairs = pd.read_csv(file2)
mapping = pd.read_csv(file3)
reviews["timestamp"] = pd.to_datetime(reviews["timestamp"], errors="coerce")
reviews["service_date"] = reviews["timestamp"].dt.strftime("%Y-%m-%d")

for df in [valid_pairs, mapping]:
    for col in ["vehicle_number", "route_id"]:
        df[col] = df[col].astype("string").str.strip()
    if "route_name" in df.columns:
        df["route_name"] = df["route_name"].astype("string").str.strip()

mapping["service_date"] = pd.to_datetime(mapping["service_date"], errors="coerce").dt.strftime("%Y-%m-%d")
valid_pairs = valid_pairs.dropna(subset=["vehicle_number", "route_id"]).drop_duplicates(["vehicle_number", "route_id"])
mapping = mapping.dropna(subset=["service_date", "vehicle_number", "route_id","driver_id", "conductor_id"])
mapping = mapping.merge(valid_pairs[["vehicle_number", "route_id"]], on=["vehicle_number", "route_id"],how="inner",validate="many_to_one").drop_duplicates()
rng = np.random.default_rng(42)

mapping_by_date = {}
for date, group in mapping.groupby("service_date"):
    mapping_by_date[date] = group.reset_index(drop=True)

ass_records = []
for _, review_row in reviews.iterrows():
    date = review_row["service_date"]
    selected = None
    if pd.notna(date) and date in mapping_by_date:
        daily_options = mapping_by_date[date]
        if "route_id" in reviews.columns and pd.notna(review_row["route_id"]):
            review_route = str(review_row["route_id"]).strip()
            daily_options = daily_options[daily_options["route_id"] == review_route]
        if ("vehicle_number" in reviews.columns and pd.notna(review_row["vehicle_number"])):
            review_vehicle = str(review_row["vehicle_number"]).strip()
            daily_options = daily_options[daily_options["vehicle_number"] == review_vehicle]
        if not daily_options.empty:
            selected_idx = int(rng.integers(0, len(daily_options)))
            selected = daily_options.iloc[selected_idx]

    if selected is None:
        ass_records.append({"assigned_vehicle_number": pd.NA,"assigned_route_id": pd.NA, "assigned_route_name": pd.NA, "assigned_first_stop": pd.NA, "assigned_last_stop": pd.NA, "driver_id": pd.NA, "conductor_id": pd.NA, "assignment_type": "unassigned"})
    else:
        ass_records.append({"assigned_vehicle_number": selected["vehicle_number"], "assigned_route_id": selected["route_id"],"assigned_route_name": selected.get("route_name", pd.NA),"assigned_first_stop": selected.get("first_stop", pd.NA), "assigned_last_stop": selected.get("last_stop", pd.NA), "driver_id": selected["driver_id"], "conductor_id": selected["conductor_id"], "assignment_type": "synthetic"})

df1 = pd.DataFrame(ass_records)
reviews = reviews.reset_index(drop=True)
df2 = pd.concat([reviews, df1], axis=1)

df2["is_negative"] = (df2["sentiment"].astype("string").str.strip().str.lower().eq("negative"))
df2["negative_count"] = df2["is_negative"].astype(int)
df2.to_csv(output, index=False)

print("Total reviews:", len(df2))
print("Assigned reviews:", df2["assignment_type"].eq("synthetic").sum())
print("Unassigned reviews:", df2["assignment_type"].eq("unassigned").sum())
print("Unique assigned buses:", df2["assigned_vehicle_number"].nunique())
print("Unique drivers:", df2["driver_id"].nunique())
print("Unique conductors:", df2["conductor_id"].nunique())