"""
Pytest configuration and fixtures for Crossroad tests.
"""

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_person():
    """Sample person data for testing."""
    return {
        "name": "Test Politician",
        "full_name": "Test Politician",
        "role_type": "dpr",
        "party": "PDIP",
        "province": "Jawa Tengah",
        "position": "Anggota DPR RI",
        "slug": "test-politician",
    }


@pytest.fixture
def sample_relationship():
    """Sample relationship data for testing."""
    return {
        "from_id": 1,
        "from_type": "person",
        "to_id": 2,
        "to_type": "person",
        "rel_type": "FAMILY_OF",
        "subtype": "spouse",
        "label": "Istri",
    }


@pytest.fixture
def sample_news_article():
    """Sample news article for testing."""
    return {
        "url": "https://example.com/news/123",
        "title": "Test News Article Title",
        "summary": "This is a test summary",
        "outlet": "Tempo",
        "category": "policy",
        "sentiment": "neutral",
    }
