import pytest
import requests
from unittest.mock import patch, MagicMock
from app.services.ingest_ea_data import fetch_uk_ea_sewage_spills

def test_fetch_uk_ea_sewage_spills_success():
    """Test successful data fetching with various item types."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {
                "lat": 51.5,
                "long": -0.1,
                "status": "Normal",
                "label": "Station A",
                "stationReference": "REF001"
            },
            {
                "lat": 52.0,
                "long": -1.0,
                "status": "Suspended Active",
                "label": "Station B",
                "stationReference": "REF002"
            },
            {
                # Missing coordinates, should be skipped
                "status": "Active",
                "label": "Station C",
                "stationReference": "REF003"
            },
            {
                "lat": 53.0,
                "long": -2.0
                # Missing label and status, defaults should be applied
            }
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch('app.services.ingest_ea_data.requests.get', return_value=mock_response):
        incidents = fetch_uk_ea_sewage_spills()

    assert len(incidents) == 3

    # Check first incident (Normal status -> recent_spill)
    assert incidents[0]["company_name"] == "Environment Agency (Live Data)"
    assert incidents[0]["location_name"] == "Station A"
    assert incidents[0]["lat"] == 51.5
    assert incidents[0]["lng"] == -0.1
    assert incidents[0]["status"] == "recent_spill"
    assert incidents[0]["station_reference"] == "REF001"

    # Check second incident (Suspended Active status -> active_spill)
    assert incidents[1]["location_name"] == "Station B"
    assert incidents[1]["lat"] == 52.0
    assert incidents[1]["lng"] == -1.0
    assert incidents[1]["status"] == "active_spill"
    assert incidents[1]["station_reference"] == "REF002"

    # Check third incident (Missing label and status, defaults)
    assert incidents[2]["location_name"] == "Unknown Station"
    assert incidents[2]["lat"] == 53.0
    assert incidents[2]["lng"] == -2.0
    assert incidents[2]["status"] == "recent_spill"
    assert incidents[2]["station_reference"] is None

def test_fetch_uk_ea_sewage_spills_api_error():
    """Test handling of API errors (e.g., timeout, 500 error)."""
    with patch('app.services.ingest_ea_data.requests.get', side_effect=requests.exceptions.RequestException("API Error")):
        incidents = fetch_uk_ea_sewage_spills()

    assert incidents == []

def test_fetch_uk_ea_sewage_spills_empty_items():
    """Test behavior when API returns an empty items list."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": []
    }
    mock_response.raise_for_status.return_value = None

    with patch('app.services.ingest_ea_data.requests.get', return_value=mock_response):
        incidents = fetch_uk_ea_sewage_spills()

    assert incidents == []

def test_fetch_uk_ea_sewage_spills_missing_items_key():
    """Test behavior when API returns JSON without 'items' key."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "other_key": "value"
    }
    mock_response.raise_for_status.return_value = None

    with patch('app.services.ingest_ea_data.requests.get', return_value=mock_response):
        incidents = fetch_uk_ea_sewage_spills()

    assert incidents == []
