from elasticsearch import VERSION as ELASTICSEARCH_VERSION
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


class Elasticsearch7Mapping(BaseElasticsearchMapping):
    pass


class Elasticsearch70Index(BaseElasticsearchIndex):
    """Index class implementing the Elasticsearch <7.15 API"""

    def put(self):
        self.connection.indices.create(self.name, self.backend.settings)

    def delete(self):
        try:
            self.connection.indices.delete(self.name)
        except self.NotFoundError:
            pass

    def refresh(self):
        self.connection.indices.refresh(self.name)

    def add_model(self, model):
        # Get mapping
        mapping = self.mapping_class(model)

        # Put mapping
        self.connection.indices.put_mapping(index=self.name, body=mapping.get_mapping())

    def add_item(self, item):
        # Make sure the object can be indexed
        if not class_is_indexed(item.__class__):
            return
        # Get mapping
        mapping = self.mapping_class(item.__class__)

        # Add document to index
        self.connection.index(
            self.name, mapping.get_document(item), id=mapping.get_document_id(item)
        )

    def _run_bulk(self, actions):
        bulk(self.connection, actions, index=self.name)


class Elasticsearch715Index(BaseElasticsearchIndex):
    """Index class overriding select methods to implement the Elasticsearch >=7.15 API"""

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
        self.connection.indices.put_mapping(index=self.name, body=mapping.get_mapping())

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


class Elasticsearch7SearchQueryCompiler(BaseElasticsearchSearchQueryCompiler):
    mapping_class = Elasticsearch7Mapping


class Elasticsearch70SearchResults(BaseElasticsearchSearchResults):
    def _backend_do_search(self, body, **kwargs):
        # Send the search query to the backend.
        return self.backend.connection.search(body=body, **kwargs)


class Elasticsearch715SearchResults(BaseElasticsearchSearchResults):
    def _backend_do_search(self, body, **kwargs):
        # As of Elasticsearch 7.15, the 'body' parameter is deprecated; instead, the top-level
        # keys of the body dict are now kwargs in their own right
        return self.backend.connection.search(**body, **kwargs)


class Elasticsearch7AutocompleteQueryCompiler(
    BaseElasticsearchAutocompleteQueryCompiler
):
    mapping_class = Elasticsearch7Mapping


class Elasticsearch7IndexRebuilder(BaseElasticsearchIndexRebuilder):
    pass


class Elasticsearch7AtomicIndexRebuilder(BaseElasticsearchAtomicIndexRebuilder):
    pass


class Elasticsearch70SearchBackend(BaseElasticsearchSearchBackend):
    mapping_class = Elasticsearch7Mapping
    index_class = Elasticsearch70Index
    query_compiler_class = Elasticsearch7SearchQueryCompiler
    autocomplete_query_compiler_class = Elasticsearch7AutocompleteQueryCompiler
    results_class = Elasticsearch70SearchResults
    basic_rebuilder_class = Elasticsearch7IndexRebuilder
    atomic_rebuilder_class = Elasticsearch7AtomicIndexRebuilder
    connection_class = Elasticsearch
    NotFoundError = ElasticsearchNotFoundError

    def _get_host_config_from_url(self, url):
        """Given a parsed URL, return the host configuration to be added to self.hosts"""
        use_ssl = url.scheme == "https"
        port = url.port or (443 if use_ssl else 80)

        http_auth = None
        if url.username is not None and url.password is not None:
            http_auth = (url.username, url.password)

        return {
            "host": url.hostname,
            "port": port,
            "url_prefix": url.path,
            "use_ssl": use_ssl,
            "verify_certs": use_ssl,
            "http_auth": http_auth,
        }

    def _get_options_from_host_urls(self, urls):
        """Given a list of parsed URLs, return a dict of additional options to be passed into the
        Elasticsearch constructor; necessary for options that aren't valid as part of the 'hosts' config
        """
        return {}


class Elasticsearch715SearchBackend(BaseElasticsearchSearchBackend):
    mapping_class = Elasticsearch7Mapping
    index_class = Elasticsearch715Index
    query_compiler_class = Elasticsearch7SearchQueryCompiler
    autocomplete_query_compiler_class = Elasticsearch7AutocompleteQueryCompiler
    results_class = Elasticsearch715SearchResults
    basic_rebuilder_class = Elasticsearch7IndexRebuilder
    atomic_rebuilder_class = Elasticsearch7AtomicIndexRebuilder
    connection_class = Elasticsearch
    NotFoundError = ElasticsearchNotFoundError

    def _get_host_config_from_url(self, url):
        """Given a parsed URL, return the host configuration to be added to self.hosts"""
        use_ssl = url.scheme == "https"
        port = url.port or (443 if use_ssl else 80)

        http_auth = None
        if url.username is not None and url.password is not None:
            http_auth = (url.username, url.password)

        return {
            "host": url.hostname,
            "port": port,
            "url_prefix": url.path,
            "use_ssl": use_ssl,
            "verify_certs": use_ssl,
            "http_auth": http_auth,
        }

    def _get_options_from_host_urls(self, urls):
        """Given a list of parsed URLs, return a dict of additional options to be passed into the
        Elasticsearch constructor; necessary for options that aren't valid as part of the 'hosts' config
        """
        return {}


if ELASTICSEARCH_VERSION >= (7, 15):
    SearchBackend = Elasticsearch715SearchBackend
    Elasticsearch7SearchBackend = Elasticsearch715SearchBackend
else:
    SearchBackend = Elasticsearch70SearchBackend
    Elasticsearch7SearchBackend = Elasticsearch70SearchBackend
