from playwright.sync_api import sync_playwright
import json
#3 other links used to fetch data from
# "https://chalo.com/app/live-tracking/route-map/tvDtMxom"
# "https://chalo.com/app/live-tracking/route-map/nNpflPAz"
# "https://chalo.com/app/live-tracking/route-map/mgfzBsOC" 
ROUTE_URL = ("https://chalo.com/app/live-tracking/route-map/DyJpbuis")

def handle_response(response):

    if "route-live-info" not in response.url:
        return

    print("\n============================")
    print("LIVE BUS RESPONSE FOUND")
    print("Status:", response.status)
    try:
        data = response.json()
        print("Keys:", data.keys())
        with open("live_response.json","w",encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print("Saved live_response.json")
    except Exception as e:
        print("Error reading response:", e)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.on("response", handle_response)
    page.goto(ROUTE_URL,wait_until="domcontentloaded")
    print("Browser running.")
    print("Log in if necessary and let the map load.")
    # Keep Playwright's event loop running
    page.wait_for_timeout(120_000)
    browser.close()
