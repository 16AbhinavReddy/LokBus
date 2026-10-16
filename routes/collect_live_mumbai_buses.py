
import asyncio
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright, TimeoutError as PWTimeout


CITY = "mumbai"
ROUTES_FILE = Path("mumbai_routes.json") #Must have the json file in the sme location as this python script 
OUTPUT_CSV = Path("mumbai_buses_last_hour.csv")
OUTPUT_JSON = Path("mumbai_buses_last_hour.json")

CONCURRENCY = 3
TIMEOUT_MS = 12000
MAX_PREV_SECONDS = 3600

IST = ZoneInfo("Asia/Kolkata")
def parse_buses(data, route):
    results = []

    for internal_id, raw in data.get("routeLiveInfo", {}).items():
        try:
            bus = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(bus, dict):
                continue
            number = str(bus.get("vNo") or "").strip().upper()
            timestamp = int(bus.get("tS"))
            if not number:
                continue
            results.append({"bus_number": number,"route": route.get("route_name"),"route_id": route["route_id"],"latitude": bus.get("_latitude"),"longitude": bus.get("_longitude"),"timestamp": timestamp,"internal_id": internal_id,})
        except (ValueError, TypeError):
            continue
    return results

def is_recent(timestamp, now_ms):
    prev_ms = now_ms - timestamp
    return 0 <= prev_ms <= MAX_PREV_SECONDS * 1000


def update_index(index, observations, now_ms):
    for bus in observations:
        if not is_recent(bus["timestamp"], now_ms):
            continue
        number = bus["bus_number"]
        previous = index.get(number)
        if previous is None or bus["timestamp"] > previous["timestamp"]:
            index[number] = bus


def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp / 1000,tz=IST).strftime("%Y-%m-%d %H:%M:%S")


def save_results(index):
    buses = []

    for bus in sorted(index.values(), key=lambda x: x["bus_number"]):
        row = bus.copy()
        row["last_updated_ist"] = format_timestamp(row["timestamp"])
        buses.append(row)

    OUTPUT_JSON.write_text(json.dumps(buses, indent=2),encoding="utf-8")

    if buses:
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=buses[0].keys())
            writer.writeheader()
            writer.writerows(buses)

    return buses


async def fetch_route(context, route, semaphore):
    async with semaphore:
        route_id = route["route_id"]
        url = f"https://chalo.com/app/live-tracking/route-map/{route_id}"
        page = await context.new_page()
        try:
            async with page.expect_response(lambda response: (f"/route-live-info/{CITY}/{route_id}" in response.url.split("?")[0] and response.status == 200),timeout=TIMEOUT_MS) as response_info:
                await page.goto(url,wait_until="commit",timeout=TIMEOUT_MS)
            response = await response_info.value
            data = await response.json()
            buses = parse_buses(data, route)
            return buses, True
        except PWTimeout:            
            return [], False
        except Exception as e:            
            return [], False
        finally:
            await page.close()


async def main():
    with ROUTES_FILE.open(encoding="utf-8") as f:
        loaded = json.load(f)

    routes = list({route["route_id"]: route for route in loaded if route.get("route_id")}.values())
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        login_page = await context.new_page()
        await login_page.goto("https://chalo.com/app",wait_until="commit",timeout=60000)
        print("Complete OTP login in the browser.")
        city_search = login_page.locator('input[placeholder="Search city"]')
        await city_search.wait_for(state="visible",timeout=180000)
        await city_search.fill("Mumbai")
        await login_page.get_by_text("Mumbai",exact=True).first.click(timeout=15000)
        print("Mumbai selected. Starting concurrent collection.")
        now_ms = int(time.time() * 1000)
        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [fetch_route(context, route, semaphore) for route in routes]
        responses = await asyncio.gather(*tasks)

        index = {}
        successes = 0
        failures = 0

        for observations, success in responses:
            update_index(index, observations, now_ms)
            if success:
                successes += 1
            else:
                failures += 1

        buses = save_results(index)        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

