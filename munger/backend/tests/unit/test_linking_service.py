"""Unit tests for LinkingService scoring helpers."""

from unittest.mock import MagicMock

from app.core.config import Settings
from app.models.entity import Entity
from app.services.linking_service import LinkingService


class TestLinkingServiceScoring:
    def test_hybrid_score_exact_name(self):
        svc = LinkingService(settings=Settings())
        a = Entity(id=1, name="Charlie Munger", entity_type="person")
        b = Entity(id=2, name="Charlie Munger", entity_type="person")
        vectors = {1: [1.0] + [0.0] * 767, 2: [1.0] + [0.0] * 767}
        assert svc._hybrid_score(a, b, vectors) >= svc.settings.link_auto_merge

    def test_hybrid_score_different_entities_low(self):
        svc = LinkingService(settings=Settings())
        a = Entity(id=1, name="System 1", entity_type="concept")
        b = Entity(id=2, name="System 2", entity_type="concept")
        vectors = {1: [1.0] + [0.0] * 767, 2: [0.0] * 768}
        assert svc._hybrid_score(a, b, vectors) < svc.settings.link_auto_merge

    def test_surface_forms_includes_shortform(self):
        forms = LinkingService._surface_forms("Charlie Munger")
        assert "Charlie Munger" in forms
        assert "Munger" in forms
