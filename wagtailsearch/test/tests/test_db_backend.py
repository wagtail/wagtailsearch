import unittest

from django.test import TestCase
from django.test.utils import override_settings

from wagtailsearch.test import models

from .test_backends import BackendTests


@override_settings(
    WAGTAILSEARCH_BACKENDS={
        "default": {
            "BACKEND": "wagtailsearch.backends.database.fallback",
        }
    }
)
class TestDBBackend(BackendTests, TestCase):
    backend_path = "wagtailsearch.backends.database.fallback"

    # Doesn't support ranking
    @unittest.expectedFailure
    def test_ranking(self):
        super().test_ranking()

    # Doesn't support ranking
    @unittest.expectedFailure
    def test_annotate_score(self):
        super().test_annotate_score()

    # Doesn't support ranking
    @unittest.expectedFailure
    def test_annotate_score_with_slice(self):
        super().test_annotate_score_with_slice()

    # Doesn't support ranking
    @unittest.expectedFailure
    def test_search_boosting_on_related_fields(self):
        super().test_search_boosting_on_related_fields()

    # Doesn't support searching specific fields
    @unittest.expectedFailure
    def test_search_child_class_field_from_parent(self):
        super().test_search_child_class_field_from_parent()

    # Doesn't support searching related fields
    @unittest.expectedFailure
    def test_search_on_related_fields(self):
        super().test_search_on_related_fields()

    # Doesn't support searching callable fields
    @unittest.expectedFailure
    def test_search_callable_field(self):
        super().test_search_callable_field()

    # Database backend always uses `icontains`, so always autocomplete
    @unittest.expectedFailure
    def test_incomplete_plain_text(self):
        super().test_incomplete_plain_text()

    # Database backend doesn't support Boost() query class
    @unittest.expectedFailure
    def test_boost(self):
        super().test_boost()

    def test_all_models_use_same_index(self):
        index1 = self.backend.get_index_for_model(models.Author)
        index2 = self.backend.get_index_for_model(models.Book)
        self.assertEqual(index1, index2)

    def test_reset_index(self):
        """
        After running backend.reset_index(), search should still return results (because there's no actual index to reset)
        """
        self.backend.reset_index()
        results = self.backend.search("JavaScript", models.Book)
        self.assertEqual(results.count(), 2)
