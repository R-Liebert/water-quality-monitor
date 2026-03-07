import pytest
from unittest.mock import patch, MagicMock
from app.services.ingest_ea_data import fetch_uk_ea_sewage_spills
import requests
from datetime import datetime, timezone

def test_fetch_uk_ea_sewage_spills_happy_path():
    with patch("app.services.ingest_ea_data.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "lat": 51.5,
                    "long": -0.1,
                    "status": "Active",
                    "label": "Station A",
                    "stationReference": "RefA"
                },
                {
                    "lat": 52.0,
                    "long": -1.0,
                    "status": "Suspended",
                    # Missing label
                    "stationReference": "RefB"
                },
                {
                    # Missing lat/long
                    "status": "Active",
                    "label": "Station C",
                    "stationReference": "RefC"
                }
            ]
        }
        mock_get.return_value = mock_response

        incidents = fetch_uk_ea_sewage_spills()

        assert len(incidents) == 2

        incident_a = incidents[0]
        assert incident_a["company_name"] == "Environment Agency (Live Data)"
        assert incident_a["location_name"] == "Station A"
        assert incident_a["lat"] == 51.5
        assert incident_a["lng"] == -0.1
        assert incident_a["status"] == "active_spill"
        assert incident_a["duration_hours"] == 2.0
        assert "reported_at" in incident_a
        assert incident_a["station_reference"] == "RefA"

        incident_b = incidents[1]
        assert incident_b["location_name"] == "Unknown Station"
        assert incident_b["lat"] == 52.0
        assert incident_b["lng"] == -1.0
        assert incident_b["status"] == "recent_spill"
        assert incident_b["station_reference"] == "RefB"

def test_fetch_uk_ea_sewage_spills_api_error():
    with patch("app.services.ingest_ea_data.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("API is down")

        incidents = fetch_uk_ea_sewage_spills()

        assert incidents == []

def test_fetch_uk_ea_sewage_spills_http_error():
    with patch("app.services.ingest_ea_data.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        incidents = fetch_uk_ea_sewage_spills()

        assert incidents == []
