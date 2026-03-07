import asyncio
import time
import random

# Mocking the functions from the app
async def mock_fetch_live_precipitation_forecast(lat: float, lng: float) -> float:
    # Simulate network latency
    await asyncio.sleep(0.05)
    return random.uniform(0, 20)

def mock_calculate_runoff_risk(max_precip: float) -> float:
    return max_precip / 20.0

class MockObs:
    def __init__(self):
        self.runoff_risk_score = 0.0

async def run_sequential(rows):
    updates = 0
    start_time = time.perf_counter()
    for obs, lat, lng in rows:
        if lat and lng:
            max_precip = await mock_fetch_live_precipitation_forecast(lat, lng)
            risk_score = mock_calculate_runoff_risk(max_precip)
            obs.runoff_risk_score = risk_score
            updates += 1
    end_time = time.perf_counter()
    return end_time - start_time, updates

async def run_optimized(rows):
    updates = 0
    start_time = time.perf_counter()

    coord_cache = {}
    unique_coords = []

    for _, lat, lng in rows:
        if lat and lng:
            rounded_lat = round(lat, 2)
            rounded_lng = round(lng, 2)
            key = (rounded_lat, rounded_lng)
            if key not in coord_cache:
                coord_cache[key] = None
                unique_coords.append((rounded_lat, rounded_lng))

    # Concurrent fetch for unique coordinates
    if unique_coords:
        results = await asyncio.gather(*[
            mock_fetch_live_precipitation_forecast(lat, lng)
            for lat, lng in unique_coords
        ])

        for i, key in enumerate(unique_coords):
            coord_cache[key] = results[i]

    for obs, lat, lng in rows:
        if lat and lng:
            rounded_lat = round(lat, 2)
            rounded_lng = round(lng, 2)
            max_precip = coord_cache[(rounded_lat, rounded_lng)]
            risk_score = mock_calculate_runoff_risk(max_precip)
            obs.runoff_risk_score = risk_score
            updates += 1

    end_time = time.perf_counter()
    return end_time - start_time, updates

async def main():
    # Generate 50 rows, with some overlapping coordinates (rounded to 2 decimal places)
    # Let's say we have 10 unique locations, each repeated 5 times but with slight variations
    rows = []
    base_coords = [(51.5074 + i*0.01, -0.1278 + i*0.01) for i in range(10)]
    for i in range(50):
        base_lat, base_lng = base_coords[i % 10]
        # Add small variation that doesn't change the 2rd decimal place mostly
        lat = base_lat + random.uniform(-0.001, 0.001)
        lng = base_lng + random.uniform(-0.001, 0.001)
        rows.append((MockObs(), lat, lng))

    print(f"Benchmarking with {len(rows)} observations and ~10 unique weather regions...")

    seq_time, seq_updates = await run_sequential(rows)
    print(f"Sequential approach: {seq_time:.4f}s ({seq_updates} updates)")

    opt_time, opt_updates = await run_optimized(rows)
    print(f"Optimized approach:  {opt_time:.4f}s ({opt_updates} updates)")

    improvement = (seq_time - opt_time) / seq_time * 100
    print(f"Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
