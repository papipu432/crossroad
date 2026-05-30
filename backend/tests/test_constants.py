"""
Tests for constants.py - seed data and configuration.
"""

import pytest
from constants import (
    PARTY_COLORS,
    KNOWN_PARTIES,
    SEED_OFFICIALS,
    OFFICIAL_SOURCES,
    NEWS_SOURCES,
    NEWS_CATEGORIES,
)


class TestPartyColors:
    """Test party color mappings."""

    def test_all_known_parties_have_colors(self):
        """Every known party should have a color defined."""
        for party in KNOWN_PARTIES:
            assert party in PARTY_COLORS, f"Party {party} missing color"

    def test_parties_are_unique(self):
        """Party colors should contain unique entries."""
        colors = list(PARTY_COLORS.values())
        assert len(colors) == len(set(colors)), "Duplicate party colors found"


class TestSeedOfficials:
    """Test seed officials list."""

    def test_no_duplicate_names(self):
        """No duplicate official names in seed list."""
        names = [o["name"] for o in SEED_OFFICIALS]
        assert len(names) == len(set(names)), "Duplicate names in seed officials"

    def test_all_have_required_fields(self):
        """All officials should have required fields."""
        required = ["name", "role_type", "party"]
        for official in SEED_OFFICIALS:
            for field in required:
                assert field in official, f"Missing {field} in {official['name']}"

    def test_valid_role_types(self):
        """All officials should have valid role types."""
        valid_roles = {
            "presiden",
            "wapres",
            "menteri",
            "dpr",
            "dprd",
            "gubernur",
            "bupati",
            "walikota",
        }
        for official in SEED_OFFICIALS:
            role = official.get("role_type")
            assert role in valid_roles, (
                f"Invalid role_type: {role} for {official['name']}"
            )


class TestNewsSources:
    """Test news source configuration."""

    def test_all_sources_have_required_fields(self):
        """All news sources should have name, search, and base."""
        required = ["name", "search", "base"]
        for source in NEWS_SOURCES:
            for field in required:
                assert field in source, f"Missing {field} in {source}"

    def test_news_categories_have_keywords(self):
        """All news categories should have keyword lists."""
        for category, keywords in NEWS_CATEGORIES.items():
            assert isinstance(keywords, list), (
                f"Keywords for {category} should be a list"
            )
            assert len(keywords) > 0, f"No keywords for {category}"
