from playwright.sync_api import sync_playwright
import json

ROUTE_URL = ("https://chalo.com/app/live-tracking/route-map/DyJpbuis")
def handle_response(response):

    if "route-live-info" not in response.url:
        return
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
    page.wait_for_timeout(120_000)
    browser.close()
