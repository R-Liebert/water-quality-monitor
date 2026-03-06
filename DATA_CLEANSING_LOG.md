# Data Cleansing & Validation Process

## Objective
To transition the platform from a "demo" state (populated with mock risk alerts) into a "production-ready" state by stripping all simulated metrics from the 1km geographic segments. This ensures that when the live Celery workers begin ingesting real satellite and terrestrial data, there is zero risk of mock data contaminating the analysis.

## Validation Rules Executed
The `scripts/cleanse_segment_data.py` script was built to iterate over the entire UK 1km segment dataset and enforce the following strict rules:

1.  **State Reset:** The `status` property of every single segment is forcefully overwritten to `"nodata"`. All simulated `"critical"`, `"warning"`, and `"normal"` states are purged.
2.  **Nullification of Quantitative Fields:** Any field representing a computed or ingested metric (e.g., `risk_score`, `turbidity`, `hydration_index`) is strictly set to `null` (None in Python). This prevents `0.0` from being falsely interpreted as a "healthy/zero-risk" reading.
3.  **Semantic Standardization:** The `explanation` string attached to each segment is stripped of mock text (like "Heavy fertilizer runoff") and replaced with a uniform system state message: *"Awaiting real-time telemetry from satellite or terrestrial sensors."*
4.  **Geometry Preservation:** The coordinate arrays (`LineString`), primary keys (`segment_id`), and physical measurements (`length_m`) are verified and preserved untouched.

## Execution Log
- **Date:** March 6, 2026
- **Target:** `/data/segmented_uk_rivers.geojson`
- **Result:** Removed 21,320 instances of simulated data.
- **Verification:** Successfully verified all 26,660 1km segments now conform strictly to the 'nodata' baseline schema.
- **Deployment:** The cleansed dataset was immediately deployed to the `/frontend` directory, replacing the mock visualization.

## Visual Impact
If you load the frontend (`http://localhost:8080`), all UK river segments will now render in the designated "No Data" style (Grey, dashed lines). The system is now a blank canvas, perfectly primed to display true warnings only when the live APIs report an incident.