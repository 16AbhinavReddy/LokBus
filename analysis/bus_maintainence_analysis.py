import argparse

import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="../data/bus_reviews_merged.csv")
parser.add_argument("--output", default="bus_maintenance_analysis.csv")
args = parser.parse_args()

df = pd.read_csv(args.input)
maintenance = df[df["category"].str.lower().eq("bus maintenance") & df["assigned_vehicle_number"].notna()].assign(is_negative=lambda rows: rows["sentiment"].str.lower().eq("negative"))

result = maintenance.groupby("assigned_vehicle_number").agg(total_review_cnt=("sentiment", "size"),neg_review_cnt=("is_negative", "sum"),)
result["negative_percent"] = (100 * result["neg_review_cnt"] / result["total_review_cnt"]).round(2)
result = result[result["total_review_cnt"] >= 10]
result = result.sort_values(["negative_percent", "neg_review_cnt"], ascending=False).head(20)
result.to_csv(args.output)
