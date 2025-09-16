import sqlite3
import unittest

from unittest import skip

from django.db import connection
from django.test.testcases import TestCase
from django.test.utils import override_settings

from wagtailsearch.backends.database.sqlite.utils import fts5_available
from wagtailsearch.test import models
from wagtailsearch.test.tests.test_backends import BackendTests


@unittest.skipUnless(
    connection.vendor == "sqlite", "The current database is not SQLite"
)
@unittest.skipIf(
    sqlite3.sqlite_version_info < (3, 19, 0), "This SQLite version is not supported"
)
@unittest.skipUnless(fts5_available(), "The SQLite fts5 extension is not available")
@override_settings(
    WAGTAILSEARCH_BACKENDS={
        "default": {
            "BACKEND": "wagtailsearch.backends.database.sqlite.sqlite",
        }
    }
)
class TestSQLiteSearchBackend(BackendTests, TestCase):
    backend_path = "wagtailsearch.backends.database.sqlite.sqlite"

    @skip("The SQLite backend doesn't support boosting.")
    def test_search_boosting_on_related_fields(self):
        return super().test_search_boosting_on_related_fields()

    @skip("The SQLite backend doesn't support boosting.")
    def test_boost(self):
        return super().test_boost()

    @skip("The SQLite backend doesn't score annotations.")
    def test_annotate_score(self):
        return super().test_annotate_score()

    @skip("The SQLite backend doesn't score annotations.")
    def test_annotate_score_with_slice(self):
        return super().test_annotate_score_with_slice()

    @skip("The SQLite backend doesn't support searching on specified fields.")
    def test_autocomplete_with_fields_arg(self):
        return super().test_autocomplete_with_fields_arg()

    @skip("The SQLite backend doesn't guarantee correct ranking of results.")
    def test_ranking(self):
        return super().test_ranking()

    def test_all_models_use_same_index(self):
        index1 = self.backend.get_index_for_model(models.Author)
        index2 = self.backend.get_index_for_model(models.Book)
        self.assertEqual(index1, index2)

    def test_reset_index(self):
        """
        After running backend.reset_index(), search should return no results.
        """
        self.backend.reset_index()
        results = self.backend.search("JavaScript", models.Book)
        self.assertEqual(results.count(), 0)

    @unittest.expectedFailure
    def test_get_search_field_for_related_fields(self):
        """
        The get_search_field method of SQLiteSearchQueryCompiler supports retrieving search fields
        across relations with double-underscore notation. This is not yet supported in actual searches,
        so test this in isolation.
        """
        # retrieve an arbitrary SearchResults object to extract a compiler object from
        results = self.backend.search("JavaScript", models.Book)
        compiler = results.query_compiler
        search_field = compiler.get_search_field("authors__name")
        self.assertIsNotNone(search_field)
        self.assertEqual(search_field.field_name, "name")
