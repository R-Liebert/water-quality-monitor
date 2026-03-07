import pytest
import requests
from unittest.mock import patch
from app.services.ingest_ea_data import fetch_uk_ea_sewage_spills

def test_fetch_uk_ea_sewage_spills_request_exception():
    with patch("app.services.ingest_ea_data.requests.get") as mock_get:
        with patch("app.services.ingest_ea_data.logger.error") as mock_logger_error:
            # Setup the mock to raise RequestException
            error_message = "API is down"
            mock_get.side_effect = requests.exceptions.RequestException(error_message)

            # Call the function
            result = fetch_uk_ea_sewage_spills()

            # Verify the result is an empty list
            assert result == []

            # Verify logger.error was called
            mock_logger_error.assert_called_once()
            args, kwargs = mock_logger_error.call_args
            assert "Error fetching data from EA API:" in args[0]
            assert error_message in args[0]
