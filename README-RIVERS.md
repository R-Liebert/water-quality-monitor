# Notes on Global River Geometries

The frontend currently uses the `ne_110m_rivers_lake_centerlines.geojson` dataset from Natural Earth. As noted, this is a highly generalized 1:110 million scale dataset. It is interpolated and meant for wide zoom levels; it will not align perfectly with the high-resolution basemap or actual riverbeds when zoomed in.

## How to achieve pixel-perfect global river alignment:

To achieve true SpatialOS-level accuracy globally, you cannot load a single GeoJSON file into the browser. A global dataset of true river vector paths (like the **HydroSHEDS** or **OSM Waterways** datasets) is hundreds of gigabytes in size.

To implement this, you must migrate the frontend from raw GeoJSON to **Vector Tiles (MVT)**.

1.  **Backend Spatial Database:** Load a high-resolution global dataset (e.g., OpenStreetMap waterways) into your PostGIS database.
2.  **Tile Server:** Deploy a vector tile server like **Martin** or **pg_tileserv** alongside your FastAPI app. These servers query the PostGIS database and serve bounding-box "tiles" of vector data to the frontend only for the area the user is currently looking at.
3.  **Frontend Update:** Switch the Leaflet `L.geoJSON` implementation to a Vector Tile renderer like `Leaflet.VectorGrid` or migrate to `Mapbox GL JS` / `MapLibre GL JS`, which are designed to consume and style MVT streams effortlessly.

This architecture allows you to render pixel-perfect, highly detailed rivers across the entire globe without freezing the user's browser.