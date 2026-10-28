import argparse
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="../data/bus_reviews_merged.csv")
parser.add_argument("--output", default="driving_analysis.csv")
args = parser.parse_args()

mapping_file = Path(__file__).resolve().parents[1] / "data" / "bus_route_driver_conductor_mapping_with_names.csv"
names = pd.read_csv(mapping_file).drop_duplicates("driver_id").set_index("driver_id")["driver_name"]
df = pd.read_csv(args.input)
driving = df[df["category"].str.lower().eq("driving") & df["driver_id"].notna()].copy()
driving["driver_name"] = driving["driver_id"].map(names)
driving["is_negative"] = driving["sentiment"].str.lower().eq("negative")

result = driving.groupby("driver_id").agg(driver_name=("driver_name", "first"), total_review_cnt=("sentiment", "size"), neg_review_cnt=("is_negative", "sum"),)
result["negative_percent"] = (100 * result["neg_review_cnt"] / result["total_review_cnt"]).round(2)
result = result[result["total_review_cnt"] >= 10]
result = result.sort_values(["negative_percent", "neg_review_cnt"], ascending=False).head(20)
result.to_csv(args.output)
