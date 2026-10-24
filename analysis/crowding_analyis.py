import pandas as pd

df = pd.read_csv("../data/bus_reviews_merged.csv")

crowding = df[(df["category"].str.lower() == "crowding") & (df["sentiment"].str.lower() == "negative")]
result = crowding.groupby(["assigned_route_id", "assigned_route_name"]).size().reset_index(name="negative_crowding_reports")
result = result[result["negative_crowding_reports"] >= 5].sort_values("negative_crowding_reports", ascending=False)

print(result.to_string(index=False))
result.to_csv("frequently_crowded_routes.csv", index=False)
