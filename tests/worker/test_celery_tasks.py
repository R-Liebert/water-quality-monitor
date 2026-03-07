import sys
from unittest.mock import MagicMock, patch
import pytest

# Since the environment is restricted and dependencies are missing,
# we must mock them. To avoid global pollution of sys.modules,
# we will use a fixture to manage the mocks.

@pytest.fixture(autouse=True)
def mock_dependencies():
    """Fixture to mock all missing dependencies for the duration of the test module."""
    # Store original modules
    original_modules = sys.modules.copy()

    # 1. Mock celery so the @task decorator doesn't replace the function with a Mock
    mock_celery = MagicMock()
    def mock_task_decorator(func):
        return func
    mock_celery.Celery.return_value.task = mock_task_decorator
    mock_celery.Celery.return_value.on_after_configure.connect = lambda f: f

    # Setup mocks
    sys.modules["celery"] = mock_celery
    sys.modules["celery.schedules"] = MagicMock()
    sys.modules["requests"] = MagicMock()
    sys.modules["httpx"] = MagicMock()
    sys.modules["sqlalchemy"] = MagicMock()
    sys.modules["app.core.config"] = MagicMock()
    sys.modules["app.db.session"] = MagicMock()
    sys.modules["app.models.waterway"] = MagicMock()
    sys.modules["app.services.copernicus_service"] = MagicMock()
    sys.modules["app.services.ingest_weather"] = MagicMock()

    yield

    # Restore original modules to prevent pollution
    sys.modules.clear()
    sys.modules.update(original_modules)

def test_fetch_sewage_spills_task():
    """Test that fetch_sewage_spills correctly formats the result message."""
    # We must import inside the test because the module-level imports in celery_app
    # require the mocks from the fixture to be active.
    from app.worker.celery_app import fetch_sewage_spills

    with patch("app.worker.celery_app.fetch_uk_ea_sewage_spills") as mock_fetch:
        # Mock the return value of the EA data fetcher
        mock_fetch.return_value = [
            {"id": 1, "location": "Thames"},
            {"id": 2, "location": "Avon"}
        ]

        # Call the task directly
        result = fetch_sewage_spills()

        # Verify the result string
        assert result == "Processed 2 sewage incidents."

        # Verify the mock was called
        mock_fetch.assert_called_once()

def test_fetch_sewage_spills_task_empty():
    """Test that fetch_sewage_spills handles empty results correctly."""
    from app.worker.celery_app import fetch_sewage_spills

    with patch("app.worker.celery_app.fetch_uk_ea_sewage_spills") as mock_fetch:
        # Mock empty return value
        mock_fetch.return_value = []

        result = fetch_sewage_spills()

        assert result == "Processed 0 sewage incidents."
        mock_fetch.assert_called_once()
