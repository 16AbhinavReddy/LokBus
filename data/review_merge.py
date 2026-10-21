import pandas as pd

file1 = "bus_reviews_enriched.csv"
file2 = "../bus_maintainence_reviews_enriched.csv"
out1 = "bus_reviews_merged.csv"

df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)

df1["original_review_id"] = df1["review_id"]
df2["original_review_id"] = df2["review_id"]
df1["source_dataset"] = "general_reviews"
df2["source_dataset"] = "maintenance_crowding_reviews"

df = pd.concat([df1, df2], ignore_index=True,sort=False)
df["review_id"] = range(1, len(df) + 1)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.sort_values("timestamp", na_position="last").reset_index(drop=True)
df.to_csv(out1, index=False)
