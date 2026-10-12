import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

OUTPUT = Path("mumbai_routes.json")
queries = [f"A-{i}" for i in range(1, 11)]
routes = {}
def handle_response(response):
    if "/scheduler_v4/v5/mumbai/search" not in response.url:
        return
    if response.status != 200:
        return
    try:
        data = response.json()
        results = data.get("data", {}).get("routes", [])
        query = parse_qs(urlparse(response.url).query).get("str", [""])[0]
        old_count = len(routes)
        for route in results:
            if route.get("agency_name", "").upper() != "BEST":
                continue
            route_id = route.get("route_id")
            if not route_id:
                continue
            routes[route_id] = {"route_id": route_id,"route_name": route.get("route_name"),"first_stop": route.get("first_stop_name"),"last_stop": route.get("last_stop_name")}
        OUTPUT.write_text(json.dumps(list(routes.values()), indent=4),encoding="utf-8")

        print(
            f"Query: {query!r} | "
            f"Returned: {len(results)} | "
            f"New BEST IDs: {len(routes) - old_count} | "
            f"Total: {len(routes)}"
        )

    except Exception as e:
        print("Response processing error:", e)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.on("response", handle_response)
    page.goto("https://chalo.com/app",wait_until="commit",timeout=60000)    
    print("Complete OTP login in the browser.")
    city_search = page.locator('input[placeholder="Search city"]')

    city_search.wait_for(state="visible",timeout=180000)    
    city_search.fill("Mumbai")
    page.get_by_text("Mumbai",exact=True).first.click(timeout=15000)
    print("Mumbai selected")    
    route_search = page.locator(".search-container").filter(has_text="Enter destination or bus number")
    route_search.wait_for(state="visible",timeout=20000)
    route_search.click()

    
    search_box = page.locator('input[type="text"]:visible').first
    print("Route search opened")    
    for query in queries:
        print("Searching:", query)
        search_box.fill(query)       
        page.wait_for_timeout(2000)

    print("\nDiscovery completed")
    print("Total unique BEST route IDs:", len(routes))

    browser.close()
