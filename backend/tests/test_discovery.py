"""
Tests for discovery crawler - party normalization.
"""

import pytest
from agents.discovery import normalize_party, PARTY_ALIASES


class TestPartyNormalization:
    """Test party name normalization."""

    def test_known_parties(self):
        """Test normalization of standard party names."""
        assert normalize_party("PDIP") == "PDIP"
        assert normalize_party("Gerindra") == "Gerindra"
        assert normalize_party("Golkar") == "Golkar"

    def test_party_aliases(self):
        """Test normalization of party aliases."""
        assert normalize_party("PDI-P") == "PDIP"
        assert normalize_party("PDI PERJUANGAN") == "PDIP"
        assert normalize_party("GERINDRA") == "Gerindra"
        assert normalize_party("GOLKAR") == "Golkar"
        assert normalize_party("PARTAI GOLKAR") == "Golkar"

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert normalize_party("pdiP") == "PDIP"
        assert normalize_party("GOLKAR") == "Golkar"

    def test_unknown_party(self):
        """Test that unknown parties return None."""
        assert normalize_party("Unknown Party") is None
        assert normalize_party("") is None
        assert normalize_party(None) is None

    def test_all_aliases_resolve(self):
        """All defined aliases should resolve to a known party."""
        for party, aliases in PARTY_ALIASES.items():
            for alias in aliases:
                result = normalize_party(alias)
                assert result == party, f"Alias {alias} should resolve to {party}"
