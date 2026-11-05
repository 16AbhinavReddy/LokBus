import argparse
import csv
import json
import random
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

MODEL = "mlx-community/Qwen2.5-3B-Instruct-4bit"
FIELDS = ["review_id", "category", "scenario", "sentiment", "severity", "rating", "route", "timestamp", "time_of_day", "review"]
SCENARIOS = {
    "Crowding": {
        "Positive": ["plenty of seats", "comfortable standing space", "uncrowded off-peak bus", "orderly boarding", "enough space for bags", "comfortable peak-hour occupancy", "easy exit at stops", "seats available for elderly passengers"],
        "Negative": ["severely overcrowded bus", "no seats available", "packed aisle", "rush-hour congestion", "difficulty boarding", "difficulty getting off", "passengers squeezed near doors", "insufficient standing space", "crowded bus stop boarding", "no room for bags"],
    },
    "Bus Maintenance": {
        "Positive": ["clean floors", "clean windows", "comfortable seats", "well-maintained seat cushions", "secure grab handles", "working hanging straps", "working air conditioning", "well-kept interior", "clean handrails", "well-maintained doors"],
        "Negative": ["dirty floor", "stained seats", "torn seat cushions", "broken hanging strap", "loose grab handle", "damaged seat", "broken window latch", "air conditioning not working", "bad smell inside bus", "leaking roof", "broken interior light", "sticky handrails"],
    },
}


def get_period(hour):
    if 5 <= hour < 12:
        return "Morning"
    if 12 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 21:
        return "Evening"
    return "Night"


def random_timestamp(rng):
    start = datetime(2025, 1, 1)
    end = datetime(2026, 10, 1)
    seconds = rng.randint(0, int((end - start).total_seconds()))
    return start + timedelta(seconds=seconds)


def clean_text(text):
    text = " ".join(str(text).strip().strip('"').split())
    return text


def parse_json_array(text):
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```\s*$", "", text)
    begin, end = text.find("["), text.rfind("]")
    if begin < 0 or end < begin:
        return None
    try:
        data = json.loads(text[begin:end + 1])
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


def make_jobs(per_category, rng):
    jobs = []
    for category, by_sentiment in SCENARIOS.items():
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


def request_batch(model, tokenizer, tasks, sampler):
    req = [{"id": i, "scenario": job["scenario"]} for i, job in enumerate(tasks)]
    category, sentiment = tasks[0]["category"], tasks[0]["sentiment"]
    instruction = (
        f"Write exactly {len(tasks)} distinct, realistic, first-person city bus passenger reviews.\n"
        f"Category: {category}. Sentiment: {sentiment}.\n"
        "Write about the EXACT assigned scenario for each id. Only discuss this category, "
        "not driving, fares, or unrelated conductors. Use natural everyday English with diverse "
        "vocabulary, voice, lengths (10 to 48 words), and sentence structures. "
        "Some reviews may be one sentence; others two. "
        "Do not include names or personal details. Do not say the reviews are synthetic.\n"
        "Output strictly a JSON array with one object per id, each with keys id (integer) and review (string). "
        "No explanations, no Markdown.\n"
        f"Requirements:\n{json.dumps(req, ensure_ascii=False)}"
    )
    prompt = tokenizer.apply_chat_template(
        [{"role": "system", "content": "You write scenario-faithful synthetic public transit reviews and valid JSON."},
         {"role": "user", "content": instruction}],
        tokenize=False, add_generation_prompt=True,
    )
    text = generate(model, tokenizer, prompt=prompt, max_tokens=650, sampler=sampler, verbose=False)
    rows = parse_json_array(text)
    if rows is None:
        return {}
    found = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        index, review = row.get("id"), clean_text(row.get("review", ""))
        if type(index) is int and 0 <= index < len(tasks) and 7 <= len(review.split()) <= 75:
            found.setdefault(index, review)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=1500)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--output", default="bus_reviews.csv")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if args.per_category < 1 or args.batch_size < 1 or args.batch_size > 8:
        ap.error("--per-category must be positive, and --batch-size must be 1 to 8")
    rng = random.Random(args.seed)
    jobs = make_jobs(args.per_category, rng)
    batches = batches_by_group(jobs, args.batch_size)
    rng.shuffle(batches)
    print(f"Loading {MODEL} (first run downloads weights)", flush=True)
    model, tokenizer = load(MODEL)
    sampler = make_sampler(temp=0.8, top_p=0.9)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    counts = Counter()
    written = 0
    failed = []
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for n, batch in enumerate(batches, 1):
            remaining = list(batch)
            for attempt in range(4):
                if not remaining:
                    break
                received = request_batch(model, tokenizer, remaining, sampler)
                next_remaining = []
                for idx, job in enumerate(remaining):
                    review = received.get(idx, "")
                    normalized = re.sub(r"\W+", "", review.lower())
                    if not review or normalized in seen:
                        next_remaining.append(job)
                        continue
                    seen.add(normalized)
                    timestamp = random_timestamp(rng)
                    sentiment = job["sentiment"]
                    writer.writerow({
                        "review_id": written + 1,
                        "category": job["category"],
                        "scenario": job["scenario"],
                        "sentiment": sentiment,
                        "severity": rng.choice(["Low", "Medium", "High"]) if sentiment == "Negative" else "None",
                        "rating": rng.choice([1, 2]) if sentiment == "Negative" else rng.choice([4, 5]),
                        "route": f"Route {rng.randint(1, 25)}",
                        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "time_of_day": get_period(timestamp.hour),
                        "review": review,
                    })
                    written += 1
                    counts[(job["category"], sentiment)] += 1
                remaining = next_remaining
            failed.extend(remaining)
            f.flush()  # Keep the output up to date throughout long runs.
            if n % 25 == 0 or n == len(batches):
                print(f"Batch {n}/{len(batches)} | saved {written}/{len(jobs)} | unresolved {len(failed)}", flush=True)
    if failed:
        missing = output.with_suffix(".missing.json")
        missing.write_text(json.dumps(failed, indent=2), encoding="utf-8")
        print(f"WARNING: {len(failed)} items could not be generated. Details: {missing}")
    print(f"Saved {written} reviews to {output}")
    for (category, sentiment), count in sorted(counts.items()):
        print(f"  {category} / {sentiment}: {count}")
    print("Note: Scenario relevance, sentiment, and severity still require quality checks.")


if __name__ == "__main__":
    main()
