from opensearchpy import NotFoundError as OpenSearchNotFoundError
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

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


class OpenSearch3Mapping(BaseElasticsearchMapping):
    pass


class OpenSearch3Index(BaseElasticsearchIndex):
    def put(self):
        self.connection.indices.create(index=self.name, body=self.backend.settings)

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
            body=mapping.get_document(item),
            id=mapping.get_document_id(item),
        )

    def _run_bulk(self, actions):
        bulk(self.connection, actions, index=self.name)


class OpenSearch3SearchQueryCompiler(BaseElasticsearchSearchQueryCompiler):
    mapping_class = OpenSearch3Mapping


class OpenSearch3SearchResults(BaseElasticsearchSearchResults):
    def _backend_do_search(self, body, index, **kwargs):
        return self.backend.connection.search(body=body, index=index, params=kwargs)


class OpenSearch3AutocompleteQueryCompiler(BaseElasticsearchAutocompleteQueryCompiler):
    mapping_class = OpenSearch3Mapping


class OpenSearch3IndexRebuilder(BaseElasticsearchIndexRebuilder):
    pass


class OpenSearch3AtomicIndexRebuilder(BaseElasticsearchAtomicIndexRebuilder):
    pass


class OpenSearch3SearchBackend(BaseElasticsearchSearchBackend):
    mapping_class = OpenSearch3Mapping
    index_class = OpenSearch3Index
    query_compiler_class = OpenSearch3SearchQueryCompiler
    autocomplete_query_compiler_class = OpenSearch3AutocompleteQueryCompiler
    results_class = OpenSearch3SearchResults
    basic_rebuilder_class = OpenSearch3IndexRebuilder
    atomic_rebuilder_class = OpenSearch3AtomicIndexRebuilder
    connection_class = OpenSearch
    NotFoundError = OpenSearchNotFoundError

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


SearchBackend = OpenSearch3SearchBackend
