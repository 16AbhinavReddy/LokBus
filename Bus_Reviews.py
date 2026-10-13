import argparse
import random

scenarios = {
    "Crowding": {
        "Positive": ["plenty of seats", "comfortable standing space", "uncrowded off-peak bus", "orderly boarding", "enough space for bags", "comfortable peak-hour occupancy", "easy exit at stops", "seats available for elderly passengers"],
        "Negative": ["severely overcrowded bus", "no seats available", "packed aisle", "rush-hour congestion", "difficulty boarding", "difficulty getting off", "passengers squeezed near doors", "insufficient standing space", "crowded bus stop boarding", "no room for bags"],
    },
    "Bus Maintenance": {
        "Positive": ["clean floors", "clean windows", "comfortable seats", "well-maintained seat cushions", "secure grab handles", "working hanging straps", "working air conditioning", "well-kept interior", "clean handrails", "well-maintained doors"],
        "Negative": ["dirty floor", "stained seats", "torn seat cushions", "broken hanging strap", "loose grab handle", "damaged seat", "broken window latch", "air conditioning not working", "bad smell inside bus", "leaking roof", "broken interior light", "sticky handrails"],
    },
}


def make_jobs(per_category, rng):
    jobs = []
    for category, by_sentiment in scenarios.items():
        positive = per_category // 2
        negative = per_category - positive
        for sentiment, count in [("Positive", positive), ("Negative", negative)]:
            options = by_sentiment[sentiment]
            for index in range(count):
                jobs.append({"category": category, "sentiment": sentiment, "scenario": options[index % len(options)]})
    rng.shuffle(jobs)
    return jobs


def batches_by_group(jobs, batch_size):
    groups = {}
    for item in jobs:
        key = (item["category"], item["sentiment"])
        groups.setdefault(key, []).append(item)
    batches = []
    for items in groups.values():
        batches.extend(items[i:i + batch_size] for i in range(0, len(items), batch_size))
    return batches



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-category", type=int, default=1500)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.per_category < 1 or not 1 <= args.batch_size <= 8:
        parser.error("--per-category must be positive and --batch-size must be 1 to 8")

    rng = random.Random(args.seed)
    jobs = make_jobs(args.per_category, rng)
    batches = batches_by_group(jobs, args.batch_size)
    print(f"Planned {len(jobs)} reviews in {len(batches)} batches")
    print("First five planned reviews:")
    for job in jobs[:5]:
        print(job)


if __name__ == "__main__":
    main()
