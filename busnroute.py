import json
from pathlib import Path
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CITY = "mumbai"
ROUTES_FILE = Path("mumbai_routes.json")
OBSERVATIONS_FILE = Path("all_bus_observations.json")
BUSES_FILE = Path("all_buses.json")
with ROUTES_FILE.open(encoding="utf-8") as f:
    routes = json.load(f)
routes = list({route["route_id"]: route for route in routes if route.get("route_id")}.values())
observations = []
successful_routes = []
failed_routes = []


def extract_buses(data, route):
    buses = []
    for internal_id, raw in data.get("routeLiveInfo", {}).items():
        try:
            bus = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(bus, dict):
                continue
            vehicle_number = str(bus.get("vNo") or "").strip()
            if not vehicle_number:
                continue
            buses.append({"vehicle_number": vehicle_number,"route_id": route["route_id"],"route_name": route.get("route_name"),"first_stop": route.get("first_stop"),"last_stop": route.get("last_stop"),"latitude": bus.get("_latitude"),
                "longitude": bus.get("_longitude"),"timestamp": bus.get("tS"),"internal_id": internal_id})
        except (ValueError, TypeError):
            continue
    return buses


def save_results():
    OBSERVATIONS_FILE.write_text(
        json.dumps(observations, indent=2),encoding="utf-8")

    
    bus_index = {}

    for observation in observations:
        number = observation["vehicle_number"].upper()

        if number not in bus_index:
            bus_index[number] = {"vehicle_number": number,"observations": []}
        bus_index[number]["observations"].append(observation)    
    for bus in bus_index.values():
        bus["observations"].sort(key=lambda x: x.get("timestamp") or 0,reverse=True)

    BUSES_FILE.write_text(json.dumps(bus_index, indent=2),encoding="utf-8")
    return bus_index


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto("https://chalo.com/app",wait_until="commit",timeout=60000)
    print("Complete phone-number and OTP login in the browser.")
    city_search = page.locator('input[placeholder="Search city"]')

    city_search.wait_for(state="visible",timeout=180000)
    city_search.fill("Mumbai")

    page.get_by_text("Mumbai",exact=True).first.click(timeout=15000)

    print("Mumbai selected.")
    print("Starting collection...\n")
    for i, route in enumerate(routes, start=1):
        route_id = route["route_id"]
        url = (f"https://chalo.com/app/live-tracking/route-map/{route_id}")
        print(f"[{i}/{len(routes)}] {route.get('route_name')} ({route_id})")

        try:
            with page.expect_response(lambda response: (f"/route-live-info/{CITY}/{route_id}" in response.url.split("?")[0] and response.status == 200),timeout=15000) as response_info:
                page.goto(url,wait_until="commit",timeout=15000)
            response = response_info.value
            data = response.json()
            buses = extract_buses(data, route)
            observations.extend(buses)
            successful_routes.append(route_id)
            print(f"  Reported buses: {len(buses)}")            
            save_results()

        except PWTimeout:
            failed_routes.append(route_id)
            print("  Timed out waiting for route data")

        except Exception as e:
            failed_routes.append(route_id)
            print("  Error:", e)       
        page.wait_for_timeout(1500)
    browser.close()



bus_index = save_results()

print("\nCOLLECTION SUMMARY")
print("----------------------------")
print("Routes discovered:", len(routes))
print("Routes fetched successfully:", len(successful_routes))
print("Routes failed:", len(failed_routes))
print("Total bus observations:", len(observations))
print("Unique physical buses:", len(bus_index))
print("Saved:", OBSERVATIONS_FILE)
print("Saved:", BUSES_FILE)
