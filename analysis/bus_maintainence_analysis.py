
import pandas as pd

df = pd.read_csv("../data/bus_reviews_merged.csv")

maintenance = df[df["category"].str.lower().eq("bus maintenance") & df["assigned_vehicle_number"].notna()]
total = maintenance.groupby("assigned_vehicle_number").size()
neg = maintenance[maintenance["sentiment"].str.lower() == "negative"].groupby("assigned_vehicle_number").size()

result = pd.DataFrame({"total_review_cnt": total, "neg_review_cnt": neg}).fillna(0)
result["neg_review"] = result["neg_review_cnt"].astype(int)
result["negative_percent"] = (100 * result["neg_review_cnt"] / result["total_review_cnt"]).round(2)
result = result[result["total_review_cnt"] >= 10]
result = result.sort_values(["negative_percent", "neg_review_cnt"],ascending=False)

print(result.head(10).to_string())
result.to_csv("bus_maintenance_analysis.csv")
