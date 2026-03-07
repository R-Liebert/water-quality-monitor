import sys
from unittest.mock import MagicMock

# Mock httpx because it's not installed in the environment
mock_httpx = MagicMock()
sys.modules["httpx"] = mock_httpx

import pytest
from app.services.ingest_weather import calculate_runoff_risk

@pytest.mark.parametrize("precip, expected", [
    (-5.0, 0.1),
    (0.0, 0.1),
    (7.5, 0.5),
    (15.0, 0.9),
    (15.1, 0.95),
    (20.0, 0.95),
])
def test_calculate_runoff_risk(precip, expected):
    result = calculate_runoff_risk(precip)
    assert result == pytest.approx(expected)
