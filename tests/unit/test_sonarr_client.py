"""
Unit tests for Sonarr client.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.clients.sonarr import SonarrClient

@pytest.fixture
def sonarr_client():
    """Returns a SonarrClient instance with a mock http_client."""
    client = SonarrClient(base_url="http://sonarr", api_key="testkey", verbose=True)
    client.http_client = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_get_queue_params(sonarr_client):
    """Test that get_queue_params returns the correct dictionary."""
    params = sonarr_client.get_queue_params()
    assert params["pageSize"] == 1000
    assert params["includeSeries"] is True

@pytest.mark.asyncio
async def test_get_media_info(sonarr_client):
    """Test get_media_info with a sample queue item."""
    queue_item = {
        "seriesId": 1,
        "episodeId": 10,
        "seasonNumber": 1,
    }
    
    sonarr_client.get_series_by_id = AsyncMock(return_value={"title": "Test Show"})
    sonarr_client.get_episode_by_id = AsyncMock(return_value={"title": "Test Episode", "episodeNumber": 1})

    media_info = await sonarr_client.get_media_info(queue_item)

    assert media_info["series"] == "Test Show"
    assert media_info["episode"] == "Test Episode"
    assert media_info["season"] == 1
    assert media_info["episode_number"] == 1

@pytest.mark.asyncio
async def test_get_series_by_id_caching(sonarr_client):
    """Test that get_series_by_id caches results."""
    sonarr_client._make_request = AsyncMock(return_value={"title": "Test Show"})
    
    # First call should trigger a network request
    await sonarr_client.get_series_by_id(1)
    sonarr_client._make_request.assert_awaited_once_with('series/1')
    
    # Second call should hit the cache
    sonarr_client._make_request.reset_mock()
    await sonarr_client.get_series_by_id(1)
    sonarr_client._make_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_get_episode_by_id_caching(sonarr_client):
    """Test that get_episode_by_id caches results."""
    sonarr_client._make_request = AsyncMock(return_value={"title": "Test Episode"})
    
    # First call
    await sonarr_client.get_episode_by_id(1)
    sonarr_client._make_request.assert_awaited_once_with('episode/1')
    
    # Second call
    sonarr_client._make_request.reset_mock()
    await sonarr_client.get_episode_by_id(1)
    sonarr_client._make_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_get_queue_items_processes_batches(sonarr_client):
    """Test that get_queue_items processes records in batches."""
    records = [{"id": i} for i in range(100)]
    sonarr_client.get_all_queue_items_paginated = AsyncMock(return_value=records)
    sonarr_client._process_queue_item = AsyncMock(return_value={"id": 1})

    await sonarr_client.get_queue_items()

    # With 100 items and a batch size of 50, _process_queue_item should be called 100 times
    assert sonarr_client._process_queue_item.await_count == 100

@pytest.mark.asyncio
async def test_get_download_updates_new_and_completed(sonarr_client):
    """Test get_download_updates identifies new, updated, and completed downloads."""
    # Previous state: two downloads
    sonarr_client.previous_status = {
        1: {"id": 1, "progress": 50, "series": "Old Show", "episode": "Old Episode", "season": 1, "episode_number": 1, "size": 100},
        3: {"id": 3, "progress": 90, "series": "Completed Show", "episode": "Completed Episode", "season": 2, "episode_number": 2, "size": 200}
    }
    
    # Current state: one download updated, one new one, one is missing (completed)
    current_downloads = [
        {"id": 2, "progress": 10, "series": "New Show", "episode": "New Episode", "season": 1, "episode_number": 1, "size": 100, "time_left": "10m", "is_new": True},
        {"id": 1, "progress": 70, "series": "Old Show", "episode": "Old Episode", "season": 1, "episode_number": 1, "size": 100, "time_left": "5m", "is_new": False},
    ]
    sonarr_client.get_active_downloads = AsyncMock(return_value=current_downloads)
    
    updates = await sonarr_client.get_download_updates()
    
    assert len(updates) == 3
    
    # Check for the new download
    new_update = next(u for u in updates if u.get('is_new'))
    assert new_update["series"] == "New Show"
    
    # Check for the updated download
    updated_download = next(u for u in updates if not u.get('is_new') and u.get('status') != 'completed')
    assert updated_download["series"] == "Old Show"
    assert updated_download["progress"] == 70

    # Check for the completed download
    completed_update = next(u for u in updates if u.get('status') == 'completed')
    assert completed_update["series"] == "Completed Show"
