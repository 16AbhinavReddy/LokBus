import json
from datetime import datetime,timezone
routes=["A211","A273","A298","A332"]
def print_locations(route):
    print("Route no: A-",route[1:])
    print("="*50)
    with open(f"routes/live_response_{route}.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for bus_id, bus_info in data["routeLiveInfo"].items():

        bus = json.loads(bus_info)

        bus_number = bus["vNo"]
        latitude = bus["_latitude"]
        longitude = bus["_longitude"]
        last_update = datetime.fromtimestamp(bus["tS"] / 1000,tz=timezone.utc)
        print(f"Bus: {bus_number}")
        print(f"Location: {latitude}, {longitude}")
        print(f"Last update: {last_update}")        
        print("------------------------")
for route in routes:
    print_locations(route)

