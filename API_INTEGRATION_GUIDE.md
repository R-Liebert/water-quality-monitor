# Real-World Data Integration Guide

This document outlines the exact APIs, credentials, and code updates required to transition this platform from mock simulations to a live, global spatialOS.

## 1. Copernicus Satellite Data (Surface Hydration & Turbidity)
**Purpose:** Global, daily scans of water bodies to measure chlorophyll-a (algae) and suspended matter (turbidity/dirt).
*   **Action 1: Register for Copernicus Data Space Ecosystem.** Go to [dataspace.copernicus.eu](https://dataspace.copernicus.eu/) and create a free account.
*   **Action 2: Generate OAuth Token.** Obtain your Client ID and Secret from your Copernicus dashboard.
*   **Action 3: Update Environment.** Add these to your `.env` file:
    ```env
    COPERNICUS_CLIENT_ID=your_id
    COPERNICUS_CLIENT_SECRET=your_secret
    ```
*   **Action 4: Code Update.** In `app/worker/celery_app.py`, update `fetch_copernicus_data` to make authenticated requests to the **Sentinel-2 L2A (or Sentinel-3 for wide-area)** OData API, requesting bounding boxes that match our 1km segments.

## 2. Weather & Precipitation Forecasts
**Purpose:** Predicting fertilizer runoff by correlating heavy rain forecasts with agricultural land bordering rivers.
*   **Action 1: Choose a Provider.** The system is currently mocked for [Open-Meteo](https://open-meteo.com/), which is excellent and free for non-commercial use (no API key required for basic tier).
*   **Action 2: Code Update.** In `app/worker/celery_app.py`, update `fetch_weather_and_calculate_risk`. Use `httpx` to ping `https://api.open-meteo.com/v1/forecast` with the `lat`/`lng` of our agricultural river segments, requesting `hourly=precipitation`.

## 3. UK Environment Agency (EA) Sewage Spills (EDM)
**Purpose:** Real-time alerts of untreated sewage being pumped into waterways by water companies.
*   **Action 1: Access the API Portal.** The UK government hosts this data via the Defra Data Services Platform: [environment.data.gov.uk](https://environment.data.gov.uk/).
*   **Action 2: Identify the specific dataset.** Search for "Event Duration Monitoring (EDM) - Storm Overflows". Note: They frequently update their specific REST endpoints, so check the latest documentation for the exact URL.
*   **Action 3: Code Update.** In `app/services/ingest_ea_data.py`, replace the `mock_api_response` array. Use `requests.get()` to hit the live Defra endpoint. You will need to parse their specific JSON/GeoJSON structure to extract the `lat`, `lng`, and `is_spilling` status.

## 4. True River Geometry (Ordnance Survey)
**Purpose:** The ultimate, centimeter-accurate geospatial paths of all UK waterways, replacing our mathematical splines.
*   **Action 1: Create an OS Data Hub account.** Go to [osdatahub.os.uk](https://osdatahub.os.uk/) and sign up.
*   **Action 2: Download OS Open Rivers.** Navigate to the Downloads API or the direct open data downloads section. Download the "OS Open Rivers" dataset in GeoPackage or GeoJSON format.
*   **Action 3: System Update.** Place the real Ordnance Survey GeoJSON file into the `/data` directory. Run the `scripts/segment_rivers.py` script against *this* real file to generate the millions of true 1km segments.

## 5. Google 3D Tiles (Optional Photorealism)
**Purpose:** Rendering the frontend over true 3D topography and buildings.
*   **Action 1: GCP Account.** Open Google Cloud Console and enable the "Map Tiles API".
*   **Action 2: Get API Key.** Generate a restricted API key.
*   **Action 3: Frontend Update.** Open `frontend/3d_map/index.html` and replace `YOUR_API_KEY` with your actual key to activate the photorealistic base layer.