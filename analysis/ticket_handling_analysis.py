import argparse
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="../data/bus_reviews_merged.csv")
parser.add_argument("--output", default="ticket_handling_analysis.csv")
args = parser.parse_args()

mapping_file = Path(__file__).resolve().parents[1] / "data" / "bus_route_driver_conductor_mapping_with_names.csv"
names = pd.read_csv(mapping_file).drop_duplicates("conductor_id").set_index("conductor_id")["conductor_name"]
df = pd.read_csv(args.input)
ticket = df[df["category"].str.lower().eq("ticket handling")& df["conductor_id"].notna()].copy()
ticket["conductor_name"] = ticket["conductor_id"].map(names)
ticket["is_negative"] = ticket["sentiment"].str.lower().eq("negative")

result = ticket.groupby("conductor_id").agg(conductor_name=("conductor_name", "first"),total_review_cnt=("sentiment", "size"),neg_review_cnt=("is_negative", "sum"))
result["negative_percent"] = (100 * result["neg_review_cnt"] / result["total_review_cnt"]).round(2)
result = result[result["total_review_cnt"] >= 10]
result = result.sort_values(["negative_percent", "neg_review_cnt"], ascending=False).head(20)
result.to_csv(args.output)
