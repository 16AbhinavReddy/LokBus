import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="../data/bus_reviews_merged.csv")
parser.add_argument("--output", default="disruptions.csv")
args = parser.parse_args()

df = pd.read_csv(args.input)
disruptions = df[df["category"].str.lower().eq("disruptions") & df["assigned_route_id"].notna()].copy()
disruptions["is_negative"] = disruptions["sentiment"].str.lower().eq("negative")

result = disruptions.groupby(["assigned_route_id", "assigned_route_name"]).agg(
    total_review_cnt=("sentiment", "size"),
    neg_review_cnt=("is_negative", "sum"),
)
result["negative_percent"] = (100 * result["neg_review_cnt"] / result["total_review_cnt"]).round(2)
result = result[result["total_review_cnt"] >= 10].sort_values(["neg_review_cnt", "negative_percent"], ascending=False).head(20)
result.to_csv(args.output)
