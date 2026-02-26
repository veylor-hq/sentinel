import time
import math
import requests

def simulate_telemetry():
    uri = "http://localhost:8000/api/public/ingress/telemetry"
    
    lat, lon = 40.7128, -74.0060
    speed = 0.0
    heading = 0.0
    battery = 100.0
    radius = 0.01
    angle = 0.0
    
    print(f"Connecting to {uri}")
    try:
        while True:
            angle += 0.05
            current_lat = lat + (radius * math.cos(angle))
            current_lon = lon + (radius * math.sin(angle))
            heading = (heading + 5) % 360
            speed = 15.5 + (math.sin(angle) * 5)
            battery = max(0.0, float(battery) - 0.1)  # Ensure it is a float
            
            payload = {
                "asset_id": "65b8c3f4e1f7a2b9d8c7e6f5", # Valid 24 char hex
                "lat": current_lat,
                "lon": current_lon,
                "speed": speed,
                "heading": heading,
                "battery": battery
            }
            
            response = requests.post(uri, json=payload)
            if response.status_code == 200:
                print(f"Sent: {current_lat:.4f}, {current_lon:.4f} | Spd: {speed:.1f} | Bat: {battery:.1f}%")
            else:
                print(f"Error {response.status_code}: {response.text}")
                
            time.sleep(1)
            
    except Exception as e:
        print(f"Simulation failed: {e}")

if __name__ == "__main__":
    simulate_telemetry()
