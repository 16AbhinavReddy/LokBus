import argparse
from pathlib import Path
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="../data/bus_reviews_merged.csv")
parser.add_argument("--output", default="monthly_negative_routes.csv")
parser.add_argument("--top", "-n", type=int, default=3)
parser.add_argument("--month", "-m", default=None)
args = parser.parse_args()

input_path = Path(args.input)
if not input_path.exists():
    input_path = Path(__file__).resolve().parents[1] / "data" / "bus_reviews_merged.csv"

df = pd.read_csv(input_path)

date_col = next((c for c in ["service_date", "timestamp", "reviewed_at", "date"] if c in df.columns), None)
if not date_col:
    ref = Path(__file__).resolve().parents[1] / "data" / "bus_reviews_merged.csv"
    if ref.exists():
        df["service_date"] = pd.read_csv(ref)["service_date"]
        date_col = "service_date"

df["month"] = pd.to_datetime(df[date_col]).dt.to_period("M").astype(str)
df["is_crowding"] = (
    df["category"].astype(str).str.strip().str.lower().eq("crowding")
    & df["sentiment"].astype(str).str.strip().str.lower().eq("negative")
)

months = [args.month] if args.month else sorted(df["month"].unique())
rows = []

for m in months:
    m_df = df[df["month"] == m]
    c_counts = (
        m_df[m_df["is_crowding"]]
        .groupby(["assigned_route_name", "assigned_route_id"])
        .size()
        .reset_index(name="crowding_reports")
    )
    t_counts = (
        m_df.groupby(["assigned_route_name", "assigned_route_id"])
        .size()
        .reset_index(name="total_reviews")
    )
    merged = pd.merge(t_counts, c_counts, on=["assigned_route_name", "assigned_route_id"], how="left").fillna(0)
    merged["crowding_reports"] = merged["crowding_reports"].astype(int)
    merged["crowding_percent"] = (100.0 * merged["crowding_reports"] / merged["total_reviews"]).round(1)
    merged = merged[merged["crowding_reports"] > 0]
    merged = merged.sort_values(
        by=["crowding_reports", "crowding_percent", "total_reviews"],
        ascending=False
    ).head(args.top)

    for rank, (_, row) in enumerate(merged.iterrows(), 1):
        rows.append({
            "month": m,
            "rank": rank,
            "route_name": row["assigned_route_name"],
            "route_id": row["assigned_route_id"],
            "crowding_reports": row["crowding_reports"],
            "total_reviews": row["total_reviews"],
            "crowding_percent": f"{row['crowding_percent']:.1f}%",
        })

result = pd.DataFrame(rows)

try:
    from tabulate import tabulate
    print(tabulate(result, headers="keys", tablefmt="grid", showindex=False))
except ImportError:
    print(result.to_string(index=False))

if args.output:
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
