from copy import deepcopy
from urllib.parse import urlparse

from django.utils.crypto import get_random_string
from elasticsearch import VERSION as ELASTICSEARCH_VERSION
from elasticsearch import Elasticsearch
from elasticsearch import NotFoundError as ElasticsearchNotFoundError
from elasticsearch.helpers import bulk

from wagtailsearch.backends.base import (
    BaseSearchBackend,
    get_model_root,
)
from wagtailsearch.backends.elasticsearch_common import (
    BaseElasticsearchAutocompleteQueryCompiler,
    BaseElasticsearchIndex,
    BaseElasticsearchMapping,
    BaseElasticsearchSearchQueryCompiler,
    BaseElasticsearchSearchResults,
)
from wagtailsearch.index import class_is_indexed
from wagtailsearch.utils import deep_update


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


class ElasticsearchIndexRebuilder:
    def __init__(self, index):
        self.index = index

    def reset_index(self):
        self.index.reset()

    def start(self):
        # Reset the index
        self.reset_index()

        return self.index

    def finish(self):
        self.index.refresh()


class ElasticsearchAtomicIndexRebuilder(ElasticsearchIndexRebuilder):
    def __init__(self, index):
        self.alias = index
        self.index = index.backend.index_class(
            index.backend, self.alias.name + "_" + get_random_string(7).lower()
        )

    def reset_index(self):
        # Delete old index using the alias
        # This should delete both the alias and the index
        self.alias.delete()

        # Create new index
        self.index.put()

        # Create a new alias
        self.index.put_alias(self.alias.name)

    def start(self):
        # Create the new index
        self.index.put()

        return self.index

    def finish(self):
        self.index.refresh()

        if self.alias.is_alias():
            # Update existing alias, then delete the old index

            # Find index that alias currently points to, we'll delete it after
            # updating the alias
            old_index = self.alias.aliased_indices()

            # Update alias to point to new index
            self.index.put_alias(self.alias.name)

            # Delete old index
            # aliased_indices() can return multiple indices. Delete them all
            for index in old_index:
                if index.name != self.index.name:
                    index.delete()

        else:
            # self.alias doesn't currently refer to an alias in Elasticsearch.
            # This means that either nothing exists in ES with that name or
            # there is currently an index with the that name

            # Run delete on the alias, just in case it is currently an index.
            # This happens on the first rebuild after switching ATOMIC_REBUILD on
            self.alias.delete()

            # Create the alias
            self.index.put_alias(self.alias.name)


class Elasticsearch70SearchBackend(BaseSearchBackend):
    mapping_class = Elasticsearch7Mapping
    index_class = Elasticsearch70Index
    query_compiler_class = Elasticsearch7SearchQueryCompiler
    autocomplete_query_compiler_class = Elasticsearch7AutocompleteQueryCompiler
    results_class = Elasticsearch70SearchResults
    basic_rebuilder_class = ElasticsearchIndexRebuilder
    atomic_rebuilder_class = ElasticsearchAtomicIndexRebuilder
    connection_class = Elasticsearch
    NotFoundError = ElasticsearchNotFoundError
    catch_indexing_errors = True
    timeout_kwarg_name = "timeout"
    default_index_name = "wagtail"

    settings = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "ngram_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["asciifolding", "lowercase", "ngram"],
                    },
                    "edgengram_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["asciifolding", "lowercase", "edgengram"],
                    },
                },
                "tokenizer": {
                    "ngram_tokenizer": {
                        "type": "ngram",
                        "min_gram": 3,
                        "max_gram": 15,
                    },
                    "edgengram_tokenizer": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 15,
                        "side": "front",
                    },
                },
                "filter": {
                    "ngram": {"type": "ngram", "min_gram": 3, "max_gram": 15},
                    "edgengram": {"type": "edge_ngram", "min_gram": 1, "max_gram": 15},
                },
            },
            "index": {
                "max_ngram_diff": 12,
            },
        }
    }

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

    def __init__(self, params):
        super().__init__(params)

        # Get settings
        self.hosts = params.pop("HOSTS", None)
        self.timeout = params.pop("TIMEOUT", 10)

        if params.pop("ATOMIC_REBUILD", False):
            self.rebuilder_class = self.atomic_rebuilder_class
        else:
            self.rebuilder_class = self.basic_rebuilder_class

        self.settings = deepcopy(
            self.settings
        )  # Make the class settings attribute as instance settings attribute
        self.settings = deep_update(self.settings, params.pop("INDEX_SETTINGS", {}))

        # Get Elasticsearch interface
        # Any remaining params are passed into the Elasticsearch constructor
        options = params.pop("OPTIONS", {})

        # If HOSTS is not set, convert URLS setting to HOSTS
        if self.hosts is None:
            es_urls = params.pop("URLS", ["http://localhost:9200"])
            # if es_urls is not a list, convert it to a list
            if isinstance(es_urls, str):
                es_urls = [es_urls]

            parsed_urls = [urlparse(url) for url in es_urls]

            self.hosts = [self._get_host_config_from_url(url) for url in parsed_urls]
            options.update(self._get_options_from_host_urls(parsed_urls))

        options[self.timeout_kwarg_name] = self.timeout

        self.connection = self.connection_class(hosts=self.hosts, **options)

        # Keep a lookup of previously instantiated instance objects, so that successive calls to get_index_for_model return the same instance
        self._indexes_by_name = {}

    def get_index_for_model(self, model):
        # Split models up into separate indices based on their root model.
        # For example, all page-derived models get put together in one index,
        # while images and documents each have their own index.
        root_model = get_model_root(model)
        index_name = f"{self.index_name}__{root_model._meta.app_label.lower()}_{root_model.__name__.lower()}"
        if index_name not in self._indexes_by_name:
            self._indexes_by_name[index_name] = self.index_class(self, index_name)

        return self._indexes_by_name[index_name]


class Elasticsearch715SearchBackend(Elasticsearch70SearchBackend):
    index_class = Elasticsearch715Index
    results_class = Elasticsearch715SearchResults


if ELASTICSEARCH_VERSION >= (7, 15):
    SearchBackend = Elasticsearch715SearchBackend
    Elasticsearch7SearchBackend = Elasticsearch715SearchBackend
else:
    SearchBackend = Elasticsearch70SearchBackend
    Elasticsearch7SearchBackend = Elasticsearch70SearchBackend
