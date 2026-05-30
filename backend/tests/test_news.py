"""
Tests for news crawler - categorization.
"""

import pytest
from crawler.news import categorize, NEWS_CATEGORIES


class TestNewsCategorization:
    """Test news article categorization."""

    def test_corruption_category(self):
        """Test corruption-related keywords."""
        assert categorize("Politikus korupsi uang negara") == "corruption"
        assert categorize("KPK tangkap tersangka") == "corruption"
        assert categorize("Suap pembahasan UU") == "corruption"

    def test_election_category(self):
        """Test election-related keywords."""
        assert categorize("Pemilu 2024 berlangsung damai") == "election"
        assert categorize("Calon gubernur maju") == "election"
        assert categorize("KPU tetapkan hasil") == "election"

    def test_family_category(self):
        """Test family-related keywords."""
        assert categorize("Istri politisi melahirkan") == "family"
        assert categorize("Anak pejabat sekolah di") == "family"

    def test_business_category(self):
        """Test business-related keywords."""
        assert categorize("Perusahaan milik politisi") == "business"
        assert categorize("Saham naik tipis") == "business"

    def test_policy_category(self):
        """Test policy-related keywords."""
        assert categorize("UU baru disahkan") == "policy"
        assert categorize("Anggaran negara naik") == "policy"

    def test_legal_category(self):
        """Test legal/judicial keywords."""
        assert categorize("Pengadilan vonis") == "legal"
        assert categorize("Hakim tetapkan") == "legal"

    def test_default_category(self):
        """Test that unknown topics get 'other' category."""
        assert categorize("Random headline here") == "other"
        assert categorize("") == "other"

    def test_category_coverage(self):
        """All categories should have keywords."""
        for category, keywords in NEWS_CATEGORIES.items():
            assert len(keywords) > 0, f"Category {category} has no keywords"
