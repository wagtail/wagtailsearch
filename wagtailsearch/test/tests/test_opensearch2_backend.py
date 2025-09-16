import unittest

from django.test import TestCase

from .elasticsearch_common_tests import ElasticsearchCommonSearchBackendTests


try:
    from opensearchpy import VERSION as OPENSEARCH_VERSION
except ImportError:
    OPENSEARCH_VERSION = (0, 0, 0)


@unittest.skipIf(OPENSEARCH_VERSION[0] != 2, "OpenSearch 2 required")
class TestOpenSearch2SearchBackend(ElasticsearchCommonSearchBackendTests, TestCase):
    backend_path = "wagtailsearch.backends.opensearch2"
