from django.core.exceptions import ImproperlyConfigured
from elasticsearch import Elasticsearch
from elasticsearch import NotFoundError as ElasticsearchNotFoundError
from elasticsearch.helpers import bulk

from wagtailsearch.backends.elasticsearch_common import (
    BaseElasticsearchAtomicIndexRebuilder,
    BaseElasticsearchAutocompleteQueryCompiler,
    BaseElasticsearchIndex,
    BaseElasticsearchIndexRebuilder,
    BaseElasticsearchMapping,
    BaseElasticsearchSearchBackend,
    BaseElasticsearchSearchQueryCompiler,
    BaseElasticsearchSearchResults,
)
from wagtailsearch.index import class_is_indexed


class Elasticsearch8Mapping(BaseElasticsearchMapping):
    pass


class Elasticsearch8Index(BaseElasticsearchIndex):
    def put(self):
        self.connection.indices.create(index=self.name, **self.backend.settings)

    def delete(self):
        try:
            self.connection.indices.delete(index=self.name)
        except self.NotFoundError:
            pass

    def refresh(self):
        self.connection.indices.refresh(index=self.name)

    def add_model(self, model):
        # Get mapping
        mapping = self.mapping_class(model)

        # Put mapping
        self.connection.indices.put_mapping(index=self.name, **mapping.get_mapping())

    def add_item(self, item):
        # Make sure the object can be indexed
        if not class_is_indexed(item.__class__):
            return

        # Get mapping
        mapping = self.mapping_class(item.__class__)

        # Add document to index
        self.connection.index(
            index=self.name,
            document=mapping.get_document(item),
            id=mapping.get_document_id(item),
        )

    def _run_bulk(self, actions):
        bulk(self.connection, actions, index=self.name)


class Elasticsearch8SearchQueryCompiler(BaseElasticsearchSearchQueryCompiler):
    mapping_class = Elasticsearch8Mapping


class Elasticsearch8SearchResults(BaseElasticsearchSearchResults):
    def _backend_do_search(self, body, **kwargs):
        # As of Elasticsearch 7.15, the 'body' parameter is deprecated; instead, the top-level
        # keys of the body dict are now kwargs in their own right
        return self.backend.connection.search(**body, **kwargs)


class Elasticsearch8AutocompleteQueryCompiler(
    BaseElasticsearchAutocompleteQueryCompiler
):
    mapping_class = Elasticsearch8Mapping


class Elasticsearch8IndexRebuilder(BaseElasticsearchIndexRebuilder):
    pass


class Elasticsearch8AtomicIndexRebuilder(BaseElasticsearchAtomicIndexRebuilder):
    pass


class Elasticsearch8SearchBackend(BaseElasticsearchSearchBackend):
    mapping_class = Elasticsearch8Mapping
    index_class = Elasticsearch8Index
    query_compiler_class = Elasticsearch8SearchQueryCompiler
    autocomplete_query_compiler_class = Elasticsearch8AutocompleteQueryCompiler
    results_class = Elasticsearch8SearchResults
    basic_rebuilder_class = Elasticsearch8IndexRebuilder
    atomic_rebuilder_class = Elasticsearch8AtomicIndexRebuilder
    connection_class = Elasticsearch
    NotFoundError = ElasticsearchNotFoundError

    timeout_kwarg_name = "request_timeout"

    def _get_host_config_from_url(self, url):
        """Given a parsed URL, return the host configuration to be added to self.hosts"""
        use_ssl = url.scheme == "https"
        port = url.port or (443 if use_ssl else 80)

        # the verify_certs and http_auth options are no longer valid in Elasticsearch 8
        return {
            "host": url.hostname,
            "port": port,
            "path_prefix": url.path,
            "scheme": url.scheme,
        }

    def _get_options_from_host_urls(self, urls):
        """Given a list of parsed URLs, return a dict of additional options to be passed into the
        Elasticsearch constructor; necessary for options that aren't valid as part of the 'hosts' config"""
        opts = {}

        basic_auth = (urls[0].username, urls[0].password)
        # Ensure that all urls have the same credentials
        if any((url.username, url.password) != basic_auth for url in urls):
            raise ImproperlyConfigured(
                "Elasticsearch host configuration is invalid. "
                "Elasticsearch 8 does not support multiple hosts with differing authentication credentials."
            )

        if basic_auth != (None, None):
            opts["basic_auth"] = basic_auth

        return opts


SearchBackend = Elasticsearch8SearchBackend
