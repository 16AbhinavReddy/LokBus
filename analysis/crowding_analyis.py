import argparse

import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="../data/bus_reviews_merged.csv")
parser.add_argument("--output", default="frequently_crowded_routes.csv")
args = parser.parse_args()
df = pd.read_csv(args.input)

crowding = df[(df["category"].str.lower() == "crowding") & (df["sentiment"].str.lower() == "negative")]
result = crowding.groupby(["assigned_route_id", "assigned_route_name"]).size().reset_index(name="negative_crowding_reports")
result = result[result["negative_crowding_reports"] >= 5].sort_values("negative_crowding_reports", ascending=False)
result = result.head(20)

result.to_csv(args.output, index=False)
