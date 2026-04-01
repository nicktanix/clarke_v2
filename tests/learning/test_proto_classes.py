"""Proto-class management tests."""

from clarke.learning.proto_classes import ProtoClassManager
from clarke.settings import TaxonomySettings


def test_check_promotion_passes():
    settings = TaxonomySettings(min_members_for_promotion=30, min_stability_score=0.75)
    manager = ProtoClassManager(settings)
    assert manager.check_promotion({"member_count": 35, "stability_score": 0.8}) is True


def test_check_promotion_fails_members():
    settings = TaxonomySettings(min_members_for_promotion=30, min_stability_score=0.75)
    manager = ProtoClassManager(settings)
    assert manager.check_promotion({"member_count": 20, "stability_score": 0.8}) is False


def test_check_promotion_fails_stability():
    settings = TaxonomySettings(min_members_for_promotion=30, min_stability_score=0.75)
    manager = ProtoClassManager(settings)
    assert manager.check_promotion({"member_count": 35, "stability_score": 0.5}) is False


def test_check_promotion_fails_both():
    settings = TaxonomySettings()
    manager = ProtoClassManager(settings)
    assert manager.check_promotion({"member_count": 0, "stability_score": 0.0}) is False
